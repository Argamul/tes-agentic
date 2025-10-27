from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status

from .models import UserRole, Permission, TokenPayload

# Set up logger
logger = logging.getLogger(__name__)


class AuthService:
    """Enhanced client for external Auth Service to verify JWT and fetch user info/roles."""

    def __init__(self) -> None:
        self.base_url: str = os.getenv("AUTH_SERVICE_URL", "")
        if not self.base_url:
            # Do not crash app startup; raise only when used
            self._configured = False
        else:
            self._configured = True

        self.timeout_seconds: float = float(os.getenv("AUTH_SERVICE_TIMEOUT_SECONDS", "5"))
        self.cache_enabled: bool = os.getenv("AUTH_CACHE_ENABLED", "false").lower() == "true"
        self.cache_ttl: int = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "300"))  # 5 minutes default
        
        # Simple in-memory cache for token validation results
        self._token_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, float] = {}

    def _is_token_cached(self, token: str) -> bool:
        """Check if token validation result is cached and not expired."""
        if not self.cache_enabled:
            return False
        
        if token not in self._token_cache:
            return False
        
        cache_time = self._cache_timestamps.get(token, 0)
        return (datetime.now(timezone.utc).timestamp() - cache_time) < self.cache_ttl

    def _cache_token_result(self, token: str, result: Dict[str, Any]) -> None:
        """Cache token validation result."""
        if not self.cache_enabled:
            return
        
        self._token_cache[token] = result
        self._cache_timestamps[token] = datetime.now(timezone.utc).timestamp()

    def _get_cached_token_result(self, token: str) -> Optional[Dict[str, Any]]:
        """Get cached token validation result."""
        if not self._is_token_cached(token):
            return None
        
        return self._token_cache.get(token)

    def _validate_token_structure(self, token: str) -> bool:
        """Enhanced JWT token structure validation."""
        if not token:
            return False
        
        # JWT tokens have 3 parts separated by dots
        parts = token.split('.')
        if len(parts) != 3:
            return False
        
        # Basic validation of each part
        for part in parts:
            if not part or len(part) == 0:
                return False
        
        # Check if token is not too long (basic security check)
        if len(token) > 8192:  # 8KB limit
            return False
        
        return True
    
    def _decode_jwt_payload(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode JWT payload without verification (for basic structure check)."""
        try:
            import base64
            import json
            
            # Split token
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # Decode payload (add padding if needed)
            payload = parts[1]
            # Add padding if needed
            missing_padding = len(payload) % 4
            if missing_padding:
                payload += '=' * (4 - missing_padding)
            
            decoded_bytes = base64.urlsafe_b64decode(payload)
            return json.loads(decoded_bytes.decode('utf-8'))
        except Exception:
            return None
    
    def _check_token_expiration(self, token: str) -> bool:
        """Check if token is expired based on exp claim."""
        payload = self._decode_jwt_payload(token)
        if not payload:
            return False
        
        exp = payload.get('exp')
        if not exp:
            # No expiration claim, assume valid for now
            return True
        
        current_time = datetime.now(timezone.utc).timestamp()
        return current_time < exp

    def _normalize_user_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize user data from auth service response."""
        # Normalize roles to list[str]
        roles: List[str] = data.get("roles") or []
        if isinstance(roles, str):
            roles = [roles]
        
        # Filter out invalid roles
        valid_roles = [role for role in roles if role in [r.value for r in UserRole]]
        data["roles"] = valid_roles
        
        # Normalize permissions to list[str]
        permissions: List[str] = data.get("permissions") or []
        if isinstance(permissions, str):
            permissions = [permissions]
        
        # Filter out invalid permissions
        valid_permissions = [perm for perm in permissions if perm in [p.value for p in Permission]]
        data["permissions"] = valid_permissions
        
        # Ensure required fields exist
        if "sub" not in data and "user_id" in data:
            data["sub"] = data["user_id"]
        
        if "email" not in data:
            data["email"] = data.get("username", "")
        
        # Add default values
        data.setdefault("is_active", True)
        data.setdefault("metadata", {})
        
        return data

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT with external service; return user payload containing roles.

        Expected response example from auth service:
        {
          "sub": "user_id",
          "email": "user@example.com",
          "username": "johndoe",
          "roles": ["admin", "teacher"],
          "permissions": ["create_user", "read_analytics"],
          "is_active": true,
          "metadata": {
            "department": "engineering",
            "last_login": "2024-01-01T00:00:00Z"
          }
        }
        """
        if not token:
            logger.warning("Token verification failed: Missing token")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

        if not self._validate_token_structure(token):
            logger.warning("Token verification failed: Invalid token structure")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")
        
        # Check token expiration locally first
        if not self._check_token_expiration(token):
            logger.warning("Token verification failed: Token expired")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

        # Check cache first
        cached_result = self._get_cached_token_result(token)
        if cached_result:
            logger.debug("Token verification: Using cached result")
            return cached_result

        if not self._configured:
            # In development mode, create a mock user for testing
            if os.getenv("ENVIRONMENT", "").lower() == "development":
                logger.info("Token verification: Using development mode mock user")
                mock_user = {
                    "sub": "dev-user-123",
                    "email": "dev@example.com",
                    "username": "devuser",
                    "roles": ["admin"],
                    "permissions": ["external_api_access"],
                    "is_active": True,
                    "metadata": {"environment": "development"}
                }
                self._cache_token_result(token, mock_user)
                return mock_user
            
            logger.error("Token verification failed: Auth service not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Auth service not configured"
            )

        url = f"{self.base_url.rstrip('/')}/verify"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                logger.debug(f"Token verification: Calling auth service at {url}")
                resp = await client.get(url, headers=headers)
            except httpx.RequestError as exc:
                logger.error(f"Token verification failed: Auth service unreachable - {exc}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY, 
                    detail=f"Auth service unreachable: {exc}"
                ) from exc

        if resp.status_code == 401:
            logger.warning("Token verification failed: Invalid or expired token from auth service")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid or expired token"
            )
        
        if resp.status_code == 403:
            logger.warning("Token verification failed: Token access denied by auth service")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Token access denied"
            )
        
        if resp.status_code != 200:
            logger.error(f"Token verification failed: Auth service returned status {resp.status_code}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, 
                detail=f"Auth service error: {resp.status_code}"
            )

        try:
            data = resp.json()
            logger.debug("Token verification: Successfully received response from auth service")
        except json.JSONDecodeError as exc:
            logger.error(f"Token verification failed: Invalid JSON response from auth service - {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, 
                detail="Invalid response from auth service"
            )

        # Normalize and validate user data
        normalized_data = self._normalize_user_data(data)
        
        # Cache the result
        self._cache_token_result(token, normalized_data)
        
        logger.info(f"Token verification successful for user: {normalized_data.get('sub', 'unknown')}")
        return normalized_data

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired JWT token using refresh token."""
        if not refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

        if not self._configured:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Auth service not configured"
            )

        url = f"{self.base_url.rstrip('/')}/refresh"
        headers = {"Content-Type": "application/json"}
        payload = {"refresh_token": refresh_token}
        
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                resp = await client.post(url, headers=headers, json=payload)
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY, 
                    detail=f"Auth service unreachable: {exc}"
                ) from exc

        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Failed to refresh token"
            )

        try:
            data = resp.json()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, 
                detail="Invalid response from auth service"
            )

        return data

    async def revoke_token(self, token: str) -> bool:
        """Revoke a JWT token."""
        if not token:
            return False

        if not self._configured:
            # In development mode, just remove from cache
            if os.getenv("ENVIRONMENT", "").lower() == "development":
                self._token_cache.pop(token, None)
                self._cache_timestamps.pop(token, None)
                return True
            
            return False

        url = f"{self.base_url.rstrip('/')}/revoke"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                resp = await client.post(url, headers=headers)
            except httpx.RequestError:
                return False

        # Remove from cache regardless of response
        self._token_cache.pop(token, None)
        self._cache_timestamps.pop(token, None)
        
        return resp.status_code == 200

    def clear_cache(self) -> None:
        """Clear the token cache."""
        self._token_cache.clear()
        self._cache_timestamps.clear()


auth_service_singleton = AuthService()






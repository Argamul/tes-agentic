from __future__ import annotations

import os
import json
import time
import logging
from typing import Dict, Set, Optional, List
from dataclasses import dataclass, asdict

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .models import UserRole, Permission, APIKeyInfo

# Set up logger
logger = logging.getLogger(__name__)


@dataclass
class APIKeyConfig:
    """Configuration for an API key."""
    key: str
    name: str
    roles: List[str] = None
    permissions: List[str] = None
    is_active: bool = True
    expires_at: Optional[int] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.permissions is None:
            self.permissions = []
        if self.metadata is None:
            self.metadata = {}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Enhanced API key middleware with role-based access control.

    Supports multiple API keys with different roles and permissions.
    Keys can be configured via environment variables or a configuration file.
    """

    def __init__(self, app, protected_prefix: str = "/external/") -> None:
        super().__init__(app)
        self.protected_prefix = protected_prefix
        self.api_keys: Dict[str, APIKeyInfo] = {}
        self._load_api_keys()

    def _load_api_keys(self) -> None:
        """Load API keys from environment variables and configuration."""
        loaded_count = 0
        
        # Load from environment variable (simple format)
        keys_env = os.getenv("EXTERNAL_API_KEYS", "")
        if keys_env:
            for key in keys_env.split(","):
                key = key.strip()
                if key:
                    self.api_keys[key] = APIKeyInfo(
                        key_id=key[:8],  # Use first 8 chars as ID
                        name=f"env-key-{key[:8]}",
                        roles=[UserRole.ADMIN.value],  # Default to admin role
                        permissions=[Permission.EXTERNAL_API_ACCESS.value],
                        created_at=int(time.time())
                    )
                    loaded_count += 1
            logger.info(f"Loaded {loaded_count} API keys from environment variables")
        
        # Load from detailed configuration (JSON format)
        config_env = os.getenv("EXTERNAL_API_KEYS_CONFIG", "")
        if config_env:
            try:
                config_data = json.loads(config_env)
                for key_config in config_data:
                    if isinstance(key_config, dict):
                        api_key_info = APIKeyInfo(
                            key_id=key_config.get("key_id", key_config["key"][:8]),
                            name=key_config.get("name", f"config-key-{key_config['key'][:8]}"),
                            roles=key_config.get("roles", []),
                            permissions=key_config.get("permissions", []),
                            is_active=key_config.get("is_active", True),
                            expires_at=key_config.get("expires_at"),
                            created_at=key_config.get("created_at", int(time.time())),
                            metadata=key_config.get("metadata", {})
                        )
                        self.api_keys[key_config["key"]] = api_key_info
                        loaded_count += 1
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse API keys configuration: {e}")
            else:
                logger.info(f"Loaded {len(self.api_keys) - loaded_count} API keys from environment config")
        
        # Load from file if specified
        config_file = os.getenv("EXTERNAL_API_KEYS_FILE", "")
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    for key_config in config_data:
                        if isinstance(key_config, dict):
                            api_key_info = APIKeyInfo(
                                key_id=key_config.get("key_id", key_config["key"][:8]),
                                name=key_config.get("name", f"file-key-{key_config['key'][:8]}"),
                                roles=key_config.get("roles", []),
                                permissions=key_config.get("permissions", []),
                                is_active=key_config.get("is_active", True),
                                expires_at=key_config.get("expires_at"),
                                created_at=key_config.get("created_at", int(time.time())),
                                metadata=key_config.get("metadata", {})
                            )
                            self.api_keys[key_config["key"]] = api_key_info
                            loaded_count += 1
            except (json.JSONDecodeError, KeyError, IOError) as e:
                logger.warning(f"Failed to load API keys from file {config_file}: {e}")
            else:
                logger.info(f"Loaded {len(self.api_keys) - loaded_count} API keys from file {config_file}")
        
        logger.info(f"Total API keys loaded: {len(self.api_keys)}")

    def _validate_api_key(self, api_key: str) -> Optional[APIKeyInfo]:
        """Validate API key and return key info if valid."""
        if not api_key:
            logger.debug("API key validation failed: Empty key")
            return None
        
        key_info = self.api_keys.get(api_key)
        if not key_info:
            logger.warning(f"API key validation failed: Unknown key {api_key[:8]}...")
            return None
        
        # Check if key is active
        if not key_info.is_active:
            logger.warning(f"API key validation failed: Inactive key {key_info.key_id}")
            return None
        
        # Check expiration
        if key_info.expires_at and time.time() > key_info.expires_at:
            logger.warning(f"API key validation failed: Expired key {key_info.key_id}")
            return None
        
        # Update usage statistics
        key_info.usage_count += 1
        key_info.last_used_at = int(time.time())
        
        logger.debug(f"API key validation successful for key {key_info.key_id}")
        return key_info

    def _check_path_permissions(self, path: str, key_info: APIKeyInfo) -> bool:
        """Check if API key has permission to access the specific path."""
        # Extract path-specific permissions from metadata
        path_permissions = key_info.metadata.get("path_permissions", {})
        
        # Check for exact path match
        if path in path_permissions:
            return path_permissions[path]
        
        # Check for prefix matches
        for allowed_path, allowed in path_permissions.items():
            if path.startswith(allowed_path) and allowed:
                return True
        
        # Default: allow if key has external API access permission
        return Permission.EXTERNAL_API_ACCESS.value in key_info.permissions

    async def dispatch(self, request: Request, call_next):
        path: str = request.url.path
        
        # Only protect routes with the configured prefix
        if not path.startswith(self.protected_prefix):
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            logger.warning(f"API key middleware: Missing X-API-Key header for {path}")
            return JSONResponse(
                {"detail": "Missing X-API-Key header"}, 
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        # Validate API key
        key_info = self._validate_api_key(api_key)
        if not key_info:
            logger.warning(f"API key middleware: Invalid API key for {path}")
            return JSONResponse(
                {"detail": "Invalid or expired API key"}, 
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        # Check path-specific permissions
        if not self._check_path_permissions(path, key_info):
            logger.warning(f"API key middleware: Permission denied for key {key_info.key_id} accessing {path}")
            return JSONResponse(
                {"detail": "API key does not have permission to access this path"}, 
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Add key info to request state for use in route handlers
        request.state.api_key_info = key_info
        request.state.user_roles = [UserRole(role) for role in key_info.roles if role in [r.value for r in UserRole]]
        request.state.user_permissions = [Permission(perm) for perm in key_info.permissions if perm in [p.value for p in Permission]]

        return await call_next(request)


def get_api_key_user(request: Request) -> Optional[APIKeyInfo]:
    """Get API key user info from request state."""
    return getattr(request.state, 'api_key_info', None)


def require_api_key_roles(*required_roles: str):
    """Dependency factory to check API key roles."""
    def dependency(request: Request):
        key_info = get_api_key_user(request)
        if not key_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key authentication required"
            )
        
        user_roles = [role for role in key_info.roles]
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient API key role. Required: {required_roles}, Key has: {user_roles}"
            )
        
        return key_info
    
    return dependency


def require_api_key_permissions(*required_permissions: str):
    """Dependency factory to check API key permissions."""
    def dependency(request: Request):
        key_info = get_api_key_user(request)
        if not key_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key authentication required"
            )
        
        user_permissions = [perm for perm in key_info.permissions]
        if not any(perm in user_permissions for perm in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient API key permissions. Required: {required_permissions}, Key has: {user_permissions}"
            )
        
        return key_info
    
    return dependency






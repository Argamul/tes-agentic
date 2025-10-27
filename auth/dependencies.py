from __future__ import annotations

from typing import List, Optional, Union, Callable, Any
from functools import wraps

from fastapi import Depends, Header, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .auth_service import auth_service_singleton
from .models import User, UserRole, Permission, TokenPayload, AccessControlResult, RolePermissions


# Security scheme for OpenAPI documentation
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    authorization: str | None = Header(default=None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> User:
    """Extract bearer token from Authorization header and verify via external service.
    
    Returns a User object with roles and permissions.
    """
    # Try to get token from Authorization header first, then from credentials
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif credentials:
        token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Missing or invalid Authorization header"
        )
    
    # Verify token with external auth service
    user_data = await auth_service_singleton.verify_token(token)
    
    # Convert to User model
    user = User(
        id=user_data.get("sub", user_data.get("user_id", "")),
        email=user_data.get("email", ""),
        username=user_data.get("username"),
        roles=[UserRole(role) for role in user_data.get("roles", []) if role in [r.value for r in UserRole]],
        permissions=[Permission(perm) for perm in user_data.get("permissions", []) if perm in [p.value for p in Permission]],
        is_active=user_data.get("is_active", True),
        metadata=user_data.get("metadata", {})
    )
    
    return user


async def get_current_user_optional(
    authorization: str | None = Header(default=None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""
    try:
        return await get_current_user(authorization, credentials)
    except HTTPException:
        return None


def require_roles(*required_roles: Union[str, UserRole]) -> Callable:
    """Dependency factory to enforce role-based access control.
    
    Args:
        *required_roles: List of required roles (can be strings or UserRole enums)
        
    Returns:
        Dependency function that checks if user has any of the required roles
    """
    # Convert string roles to UserRole enums
    roles = []
    for role in required_roles:
        if isinstance(role, str):
            try:
                roles.append(UserRole(role))
            except ValueError:
                raise ValueError(f"Invalid role: {role}")
        else:
            roles.append(role)
    
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if not user.has_any_role(roles):
            role_names = [role.value for role in roles]
            user_role_names = [role.value for role in user.roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Insufficient role. Required: {role_names}, User has: {user_role_names}"
            )
        return user
    
    return dependency


def require_permissions(*required_permissions: Union[str, Permission]) -> Callable:
    """Dependency factory to enforce permission-based access control.
    
    Args:
        *required_permissions: List of required permissions (can be strings or Permission enums)
        
    Returns:
        Dependency function that checks if user has all required permissions
    """
    # Convert string permissions to Permission enums
    permissions = []
    for perm in required_permissions:
        if isinstance(perm, str):
            try:
                permissions.append(Permission(perm))
            except ValueError:
                raise ValueError(f"Invalid permission: {perm}")
        else:
            permissions.append(perm)
    
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if not user.has_any_permission(permissions):
            perm_names = [perm.value for perm in permissions]
            user_perms = [perm.value for perm in user.get_all_permissions()]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Insufficient permissions. Required: {perm_names}, User has: {user_perms}"
            )
        return user
    
    return dependency


def require_all_permissions(*required_permissions: Union[str, Permission]) -> Callable:
    """Dependency factory to enforce that user has ALL required permissions.
    
    Args:
        *required_permissions: List of required permissions (can be strings or Permission enums)
        
    Returns:
        Dependency function that checks if user has all required permissions
    """
    # Convert string permissions to Permission enums
    permissions = []
    for perm in required_permissions:
        if isinstance(perm, str):
            try:
                permissions.append(Permission(perm))
            except ValueError:
                raise ValueError(f"Invalid permission: {perm}")
        else:
            permissions.append(perm)
    
    async def dependency(user: User = Depends(get_current_user)) -> User:
        missing_permissions = []
        for perm in permissions:
            if not user.has_permission(perm):
                missing_permissions.append(perm.value)
        
        if missing_permissions:
            user_perms = [perm.value for perm in user.get_all_permissions()]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Missing permissions: {missing_permissions}, User has: {user_perms}"
            )
        return user
    
    return dependency


def check_access_control(
    user: User,
    required_roles: Optional[List[UserRole]] = None,
    required_permissions: Optional[List[Permission]] = None,
    require_all_permissions: bool = False
) -> AccessControlResult:
    """Check if user has required access based on roles and permissions.
    
    Args:
        user: User object to check
        required_roles: List of required roles (user needs ANY of these)
        required_permissions: List of required permissions
        require_all_permissions: If True, user needs ALL permissions; if False, user needs ANY permission
        
    Returns:
        AccessControlResult with access decision and details
    """
    result = AccessControlResult(
        allowed=True,
        user_roles=[role for role in user.roles],
        user_permissions=[perm for perm in user.get_all_permissions()]
    )
    
    # Check roles
    if required_roles:
        result.required_roles = required_roles
        if not user.has_any_role(required_roles):
            result.allowed = False
            result.reason = f"User lacks required roles: {[r.value for r in required_roles]}"
            return result
    
    # Check permissions
    if required_permissions:
        result.required_permissions = required_permissions
        if require_all_permissions:
            # User needs ALL permissions
            missing_permissions = []
            for perm in required_permissions:
                if not user.has_permission(perm):
                    missing_permissions.append(perm.value)
            
            if missing_permissions:
                result.allowed = False
                result.reason = f"User lacks required permissions: {missing_permissions}"
                return result
        else:
            # User needs ANY permission
            if not user.has_any_permission(required_permissions):
                result.allowed = False
                result.reason = f"User lacks any of the required permissions: {[p.value for p in required_permissions]}"
                return result
    
    return result


# Convenience decorators for common role combinations
require_admin = require_roles(UserRole.ADMIN)
require_teacher_or_admin = require_roles(UserRole.TEACHER, UserRole.ADMIN)
require_student_or_above = require_roles(UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN)

# Convenience decorators for common permission combinations
require_user_management = require_permissions(Permission.CREATE_USER, Permission.UPDATE_USER, Permission.DELETE_USER)
require_course_management = require_permissions(Permission.CREATE_COURSE, Permission.UPDATE_COURSE, Permission.DELETE_COURSE)
require_content_management = require_permissions(Permission.CREATE_CONTENT, Permission.UPDATE_CONTENT, Permission.DELETE_CONTENT)
require_system_management = require_permissions(Permission.MANAGE_SYSTEM)
require_analytics_access = require_permissions(Permission.READ_ANALYTICS, Permission.READ_REPORTS)




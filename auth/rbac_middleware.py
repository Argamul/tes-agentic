from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Set, Union, Callable, Any
from dataclasses import dataclass
from functools import wraps

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .models import UserRole, Permission, User, AccessControlResult
from .dependencies import get_current_user_optional, check_access_control


@dataclass
class RouteProtection:
    """Configuration for protecting a route."""
    path_pattern: str
    methods: List[str] = None
    required_roles: List[UserRole] = None
    required_permissions: List[Permission] = None
    require_all_permissions: bool = False
    allow_anonymous: bool = False
    custom_check: Optional[Callable[[User], bool]] = None
    
    def __post_init__(self):
        if self.methods is None:
            self.methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        if self.required_roles is None:
            self.required_roles = []
        if self.required_permissions is None:
            self.required_permissions = []


class RBACMiddleware(BaseHTTPMiddleware):
    """Role-Based Access Control middleware for automatic route protection.
    
    This middleware automatically enforces access control based on configured
    route patterns and their required roles/permissions.
    """

    def __init__(self, app, config_file: Optional[str] = None) -> None:
        super().__init__(app)
        self.route_protections: List[RouteProtection] = []
        self._load_config(config_file)
        self._load_default_protections()

    def _load_config(self, config_file: Optional[str] = None) -> None:
        """Load RBAC configuration from file."""
        if not config_file:
            config_file = os.getenv("RBAC_CONFIG_FILE", "")
        
        if config_file and os.path.exists(config_file):
            try:
                import json
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    self._parse_config(config_data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load RBAC config from {config_file}: {e}")

    def _parse_config(self, config_data: Dict[str, Any]) -> None:
        """Parse configuration data and create route protections."""
        for route_config in config_data.get("routes", []):
            protection = RouteProtection(
                path_pattern=route_config["path_pattern"],
                methods=route_config.get("methods", ["GET", "POST", "PUT", "DELETE", "PATCH"]),
                required_roles=[UserRole(role) for role in route_config.get("required_roles", [])],
                required_permissions=[Permission(perm) for perm in route_config.get("required_permissions", [])],
                require_all_permissions=route_config.get("require_all_permissions", False),
                allow_anonymous=route_config.get("allow_anonymous", False)
            )
            self.route_protections.append(protection)

    def _load_default_protections(self) -> None:
        """Load default route protections."""
        # Admin-only routes
        self.route_protections.extend([
            RouteProtection(
                path_pattern=r"^/admin/.*",
                required_roles=[UserRole.ADMIN]
            ),
            RouteProtection(
                path_pattern=r"^/system/.*",
                required_roles=[UserRole.ADMIN],
                required_permissions=[Permission.MANAGE_SYSTEM]
            ),
            RouteProtection(
                path_pattern=r"^/users/.*/delete$",
                required_roles=[UserRole.ADMIN],
                required_permissions=[Permission.DELETE_USER]
            ),
        ])
        
        # Teacher and above routes
        self.route_protections.extend([
            RouteProtection(
                path_pattern=r"^/teacher/.*",
                required_roles=[UserRole.TEACHER, UserRole.ADMIN]
            ),
            RouteProtection(
                path_pattern=r"^/courses/.*/edit$",
                required_roles=[UserRole.TEACHER, UserRole.ADMIN],
                required_permissions=[Permission.UPDATE_COURSE]
            ),
            RouteProtection(
                path_pattern=r"^/content/.*/edit$",
                required_roles=[UserRole.TEACHER, UserRole.ADMIN],
                required_permissions=[Permission.UPDATE_CONTENT]
            ),
        ])
        
        # Student and above routes
        self.route_protections.extend([
            RouteProtection(
                path_pattern=r"^/student/.*",
                required_roles=[UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN]
            ),
            RouteProtection(
                path_pattern=r"^/courses/.*",
                required_roles=[UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN],
                required_permissions=[Permission.READ_COURSE]
            ),
            RouteProtection(
                path_pattern=r"^/questions/.*",
                required_roles=[UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN],
                required_permissions=[Permission.READ_QUESTION]
            ),
        ])
        
        # Analytics routes
        self.route_protections.extend([
            RouteProtection(
                path_pattern=r"^/analytics/.*",
                required_roles=[UserRole.TEACHER, UserRole.ADMIN],
                required_permissions=[Permission.READ_ANALYTICS]
            ),
            RouteProtection(
                path_pattern=r"^/reports/.*",
                required_roles=[UserRole.TEACHER, UserRole.ADMIN],
                required_permissions=[Permission.READ_REPORTS]
            ),
        ])
        
        # Public routes (no authentication required)
        public_patterns = [
            r"^/health$",
            r"^/docs$",
            r"^/redoc$",
            r"^/openapi\.json$",
            r"^/metrics$",
            r"^/auth/login$",
            r"^/auth/register$",
        ]
        
        for pattern in public_patterns:
            self.route_protections.append(
                RouteProtection(
                    path_pattern=pattern,
                    allow_anonymous=True
                )
            )

    def _find_matching_protection(self, path: str, method: str) -> Optional[RouteProtection]:
        """Find the first matching route protection for the given path and method."""
        for protection in self.route_protections:
            if method.upper() in protection.methods:
                if re.match(protection.path_pattern, path):
                    return protection
        return None

    async def dispatch(self, request: Request, call_next):
        path: str = request.url.path
        method: str = request.method
        
        # Find matching protection rule
        protection = self._find_matching_protection(path, method)
        
        if not protection:
            # No protection rule found, allow access
            return await call_next(request)
        
        # If anonymous access is allowed, proceed
        if protection.allow_anonymous:
            return await call_next(request)
        
        # Get current user (optional, won't raise exception if not authenticated)
        user = await get_current_user_optional(request)
        
        if not user:
            return JSONResponse(
                {"detail": "Authentication required"}, 
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check access control
        access_result = check_access_control(
            user=user,
            required_roles=protection.required_roles,
            required_permissions=protection.required_permissions,
            require_all_permissions=protection.require_all_permissions
        )
        
        if not access_result.allowed:
            return JSONResponse(
                {
                    "detail": access_result.reason,
                    "required_roles": [role.value for role in access_result.required_roles],
                    "required_permissions": [perm.value for perm in access_result.required_permissions],
                    "user_roles": [role.value for role in access_result.user_roles],
                    "user_permissions": [perm.value for perm in access_result.user_permissions]
                }, 
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Custom check if provided
        if protection.custom_check and not protection.custom_check(user):
            return JSONResponse(
                {"detail": "Custom access check failed"}, 
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Add user info to request state for use in route handlers
        request.state.current_user = user
        request.state.access_result = access_result
        
        return await call_next(request)


def rbac_protect(
    path_pattern: str,
    methods: Optional[List[str]] = None,
    required_roles: Optional[List[Union[str, UserRole]]] = None,
    required_permissions: Optional[List[Union[str, Permission]]] = None,
    require_all_permissions: bool = False,
    allow_anonymous: bool = False,
    custom_check: Optional[Callable[[User], bool]] = None
) -> Callable:
    """Decorator to protect a route with RBAC.
    
    This decorator can be used to add protection to individual routes
    without relying on the middleware's automatic pattern matching.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs (FastAPI dependency injection)
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # If no request found, call the original function
                return await func(*args, **kwargs)
            
            # Convert string roles/permissions to enums
            roles = []
            if required_roles:
                for role in required_roles:
                    if isinstance(role, str):
                        roles.append(UserRole(role))
                    else:
                        roles.append(role)
            
            permissions = []
            if required_permissions:
                for perm in required_permissions:
                    if isinstance(perm, str):
                        permissions.append(Permission(perm))
                    else:
                        permissions.append(perm)
            
            # Get current user
            user = await get_current_user_optional(request)
            
            if not user and not allow_anonymous:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if user:
                # Check access control
                access_result = check_access_control(
                    user=user,
                    required_roles=roles,
                    required_permissions=permissions,
                    require_all_permissions=require_all_permissions
                )
                
                if not access_result.allowed:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=access_result.reason
                    )
                
                # Custom check if provided
                if custom_check and not custom_check(user):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Custom access check failed"
                    )
                
                # Add user info to request state
                request.state.current_user = user
                request.state.access_result = access_result
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Convenience decorators for common protection patterns
def admin_only(func: Callable) -> Callable:
    """Decorator to restrict access to admin users only."""
    return rbac_protect(
        path_pattern=".*",
        required_roles=[UserRole.ADMIN]
    )(func)


def teacher_or_admin(func: Callable) -> Callable:
    """Decorator to restrict access to teacher and admin users."""
    return rbac_protect(
        path_pattern=".*",
        required_roles=[UserRole.TEACHER, UserRole.ADMIN]
    )(func)


def student_or_above(func: Callable) -> Callable:
    """Decorator to restrict access to student, teacher, and admin users."""
    return rbac_protect(
        path_pattern=".*",
        required_roles=[UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN]
    )(func)


def require_permission(permission: Union[str, Permission], require_all: bool = False) -> Callable:
    """Decorator to require specific permission(s)."""
    return rbac_protect(
        path_pattern=".*",
        required_permissions=[permission],
        require_all_permissions=require_all
    )

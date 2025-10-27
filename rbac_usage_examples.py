#!/usr/bin/env python3
"""
RBAC Usage Examples

This file demonstrates how to use the RBAC system in your FastAPI application.
It shows various patterns for implementing role-based and permission-based access control.
"""

from fastapi import FastAPI, Depends, HTTPException, Request
from typing import List, Optional
from auth.dependencies import (
    get_current_user, get_current_user_optional,
    require_roles, require_permissions, require_all_permissions,
    require_admin, require_teacher_or_admin, require_student_or_above,
    require_user_management, require_course_management, require_content_management,
    require_system_management, require_analytics_access
)
from auth.rbac_middleware import rbac_protect, admin_only, teacher_or_admin, student_or_above
from auth.api_key_middleware import get_api_key_user, require_api_key_roles, require_api_key_permissions
from auth.models import User, UserRole, Permission

app = FastAPI(title="RBAC Usage Examples")


# =============================================================================
# Basic Authentication Examples
# =============================================================================

@app.get("/profile")
async def get_user_profile(user: User = Depends(get_current_user)):
    """Get current user's profile - requires authentication."""
    return {
        "user_id": user.id,
        "email": user.email,
        "roles": [role.value for role in user.roles],
        "permissions": [perm.value for perm in user.get_all_permissions()]
    }


@app.get("/profile-optional")
async def get_user_profile_optional(user: Optional[User] = Depends(get_current_user_optional)):
    """Get user profile if authenticated, otherwise return public info."""
    if user:
        return {
            "authenticated": True,
            "user_id": user.id,
            "email": user.email,
            "roles": [role.value for role in user.roles]
        }
    else:
        return {
            "authenticated": False,
            "message": "Public profile information"
        }


# =============================================================================
# Role-Based Access Control Examples
# =============================================================================

@app.get("/admin-only")
async def admin_only_endpoint(user: User = Depends(require_admin)):
    """Only admins can access this endpoint."""
    return {
        "message": "Admin-only content",
        "admin_user": user.email
    }


@app.get("/teacher-content")
async def teacher_content(user: User = Depends(require_teacher_or_admin)):
    """Teachers and admins can access this endpoint."""
    return {
        "message": "Teacher/Admin content",
        "user_role": user.roles[0].value if user.roles else "unknown"
    }


@app.get("/student-content")
async def student_content(user: User = Depends(require_student_or_above)):
    """Students, teachers, and admins can access this endpoint."""
    return {
        "message": "Student+ content",
        "user_roles": [role.value for role in user.roles]
    }


@app.get("/custom-roles")
async def custom_roles_endpoint(user: User = Depends(require_roles("admin", "teacher"))):
    """Custom role requirement - admins or teachers."""
    return {
        "message": "Custom role access",
        "user_roles": [role.value for role in user.roles]
    }


# =============================================================================
# Permission-Based Access Control Examples
# =============================================================================

@app.get("/user-management")
async def user_management_endpoint(user: User = Depends(require_user_management)):
    """Requires user management permissions."""
    return {
        "message": "User management interface",
        "user_permissions": [perm.value for perm in user.get_all_permissions()]
    }


@app.get("/course-management")
async def course_management_endpoint(user: User = Depends(require_course_management)):
    """Requires course management permissions."""
    return {
        "message": "Course management interface",
        "can_create_courses": user.has_permission(Permission.CREATE_COURSE),
        "can_delete_courses": user.has_permission(Permission.DELETE_COURSE)
    }


@app.get("/analytics")
async def analytics_endpoint(user: User = Depends(require_analytics_access)):
    """Requires analytics access permissions."""
    return {
        "message": "Analytics dashboard",
        "can_read_analytics": user.has_permission(Permission.READ_ANALYTICS),
        "can_read_reports": user.has_permission(Permission.READ_REPORTS)
    }


@app.get("/specific-permission")
async def specific_permission_endpoint(user: User = Depends(require_permissions(Permission.CREATE_USER))):
    """Requires a specific permission."""
    return {
        "message": "User creation interface",
        "has_create_user_permission": user.has_permission(Permission.CREATE_USER)
    }


@app.get("/multiple-permissions")
async def multiple_permissions_endpoint(user: User = Depends(require_permissions(
    Permission.READ_ANALYTICS, 
    Permission.READ_REPORTS
))):
    """Requires any of the specified permissions."""
    return {
        "message": "Analytics or reports access",
        "can_read_analytics": user.has_permission(Permission.READ_ANALYTICS),
        "can_read_reports": user.has_permission(Permission.READ_REPORTS)
    }


@app.get("/all-permissions")
async def all_permissions_endpoint(user: User = Depends(require_all_permissions(
    Permission.CREATE_USER,
    Permission.UPDATE_USER,
    Permission.DELETE_USER
))):
    """Requires ALL specified permissions."""
    return {
        "message": "Full user management access",
        "has_all_user_permissions": True
    }


# =============================================================================
# Decorator-Based Protection Examples
# =============================================================================

@admin_only
@app.get("/decorator-admin")
async def decorator_admin_endpoint():
    """Admin-only endpoint using decorator."""
    return {"message": "Admin decorator endpoint"}


@teacher_or_admin
@app.get("/decorator-teacher")
async def decorator_teacher_endpoint():
    """Teacher+ endpoint using decorator."""
    return {"message": "Teacher decorator endpoint"}


@student_or_above
@app.get("/decorator-student")
async def decorator_student_endpoint():
    """Student+ endpoint using decorator."""
    return {"message": "Student decorator endpoint"}


@rbac_protect(
    path_pattern=".*",
    required_roles=[UserRole.ADMIN],
    required_permissions=[Permission.MANAGE_SYSTEM]
)
@app.get("/decorator-custom")
async def decorator_custom_endpoint():
    """Custom protection using decorator."""
    return {"message": "Custom decorator endpoint"}


# =============================================================================
# API Key Authentication Examples
# =============================================================================

@app.get("/external/api-status")
async def external_api_status(api_key_user = Depends(get_api_key_user)):
    """External API endpoint with API key authentication."""
    return {
        "message": "External API status",
        "api_key_id": api_key_user.key_id,
        "api_key_name": api_key_user.name
    }


@app.get("/external/admin-only")
async def external_admin_only(api_key_user = Depends(require_api_key_roles("admin"))):
    """External API endpoint requiring admin API key."""
    return {
        "message": "Admin-only external endpoint",
        "api_key_roles": api_key_user.roles
    }


@app.get("/external/teacher-access")
async def external_teacher_access(api_key_user = Depends(require_api_key_roles("admin", "teacher"))):
    """External API endpoint requiring teacher or admin API key."""
    return {
        "message": "Teacher+ external endpoint",
        "api_key_roles": api_key_user.roles
    }


@app.get("/external/permission-based")
async def external_permission_based(api_key_user = Depends(require_api_key_permissions("external_api_access"))):
    """External API endpoint requiring specific permission."""
    return {
        "message": "Permission-based external endpoint",
        "api_key_permissions": api_key_user.permissions
    }


# =============================================================================
# Custom Access Control Examples
# =============================================================================

@app.get("/resource/{resource_id}")
async def get_resource(
    resource_id: str,
    user: User = Depends(get_current_user)
):
    """Custom access control based on resource ownership."""
    
    # Simulate resource data
    resource = {
        "id": resource_id,
        "name": f"Resource {resource_id}",
        "owner_id": "user-123",  # Simulate ownership
        "public": False
    }
    
    # Check access based on role and ownership
    if user.has_role(UserRole.ADMIN):
        # Admins can access all resources
        access_level = "admin"
    elif user.has_role(UserRole.TEACHER) and resource["owner_id"] == user.id:
        # Teachers can access their own resources
        access_level = "owner"
    elif resource["public"]:
        # Public resources accessible to all authenticated users
        access_level = "public"
    else:
        # No access
        raise HTTPException(
            status_code=403,
            detail="Access denied: You don't have permission to view this resource"
        )
    
    return {
        "resource": resource,
        "access_level": access_level,
        "requested_by": user.id
    }


@app.get("/conditional-features")
async def get_conditional_features(user: User = Depends(get_current_user)):
    """Return different features based on user permissions."""
    
    features = {
        "basic_features": ["view_profile", "edit_profile"],
        "advanced_features": [],
        "admin_features": []
    }
    
    # Add features based on permissions
    if user.has_permission(Permission.CREATE_COURSE):
        features["advanced_features"].append("create_courses")
    
    if user.has_permission(Permission.READ_ANALYTICS):
        features["advanced_features"].append("view_analytics")
    
    if user.has_permission(Permission.CREATE_USER):
        features["admin_features"].append("manage_users")
    
    if user.has_permission(Permission.MANAGE_SYSTEM):
        features["admin_features"].append("system_admin")
    
    return {
        "user_id": user.id,
        "features": features,
        "total_features": sum(len(f) for f in features.values())
    }


# =============================================================================
# Request State Examples
# =============================================================================

@app.get("/request-context")
async def get_request_context(request: Request):
    """Access user information from request state (set by middleware)."""
    
    # Get user from request state (set by RBAC middleware)
    user = getattr(request.state, 'current_user', None)
    access_result = getattr(request.state, 'access_result', None)
    api_key_info = getattr(request.state, 'api_key_info', None)
    
    context = {
        "user_authenticated": user is not None,
        "api_key_authenticated": api_key_info is not None
    }
    
    if user:
        context.update({
            "user_id": user.id,
            "user_roles": [role.value for role in user.roles],
            "user_permissions": [perm.value for perm in user.get_all_permissions()]
        })
    
    if access_result:
        context.update({
            "access_allowed": access_result.allowed,
            "access_reason": access_result.reason
        })
    
    if api_key_info:
        context.update({
            "api_key_id": api_key_info.key_id,
            "api_key_roles": api_key_info.roles,
            "api_key_permissions": api_key_info.permissions
        })
    
    return context


# =============================================================================
# Error Handling Examples
# =============================================================================

@app.get("/error-examples")
async def error_examples(user: User = Depends(get_current_user)):
    """Examples of different error scenarios."""
    
    # Example 1: Check if user has specific permission
    if not user.has_permission(Permission.MANAGE_SYSTEM):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions: manage_system required"
        )
    
    # Example 2: Check if user has specific role
    if not user.has_role(UserRole.ADMIN):
        raise HTTPException(
            status_code=403,
            detail="Admin role required for this operation"
        )
    
    # Example 3: Custom business logic
    if user.id == "restricted-user":
        raise HTTPException(
            status_code=403,
            detail="This user account is restricted"
        )
    
    return {
        "message": "All checks passed",
        "user_id": user.id
    }


# =============================================================================
# Utility Endpoints
# =============================================================================

@app.get("/user-permissions")
async def get_user_permissions(user: User = Depends(get_current_user)):
    """Get detailed information about user's permissions."""
    
    all_permissions = [perm for perm in Permission]
    user_permissions = user.get_all_permissions()
    
    permission_details = {}
    for perm in all_permissions:
        permission_details[perm.value] = {
            "has_permission": user.has_permission(perm),
            "granted_by_role": any(
                RolePermissions.has_permission(role, perm) 
                for role in user.roles
            ),
            "granted_directly": perm in user.permissions
        }
    
    return {
        "user_id": user.id,
        "roles": [role.value for role in user.roles],
        "direct_permissions": [perm.value for perm in user.permissions],
        "role_permissions": [perm.value for perm in user_permissions if perm not in user.permissions],
        "all_permissions": [perm.value for perm in user_permissions],
        "permission_details": permission_details
    }


@app.get("/role-hierarchy")
async def get_role_hierarchy():
    """Get information about the role hierarchy and permissions."""
    
    hierarchy = {}
    for role in UserRole:
        permissions = RolePermissions.get_permissions(role)
        hierarchy[role.value] = {
            "permissions": [perm.value for perm in permissions],
            "permission_count": len(permissions)
        }
    
    return {
        "role_hierarchy": hierarchy,
        "total_roles": len(UserRole),
        "total_permissions": len(Permission)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

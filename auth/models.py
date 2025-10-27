from __future__ import annotations

from enum import Enum
from typing import List, Set, Dict, Any, Optional
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class Permission(str, Enum):
    """System permissions."""
    # User management
    CREATE_USER = "create_user"
    READ_USER = "read_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    
    # Course management
    CREATE_COURSE = "create_course"
    READ_COURSE = "read_course"
    UPDATE_COURSE = "update_course"
    DELETE_COURSE = "delete_course"
    
    # Content management
    CREATE_CONTENT = "create_content"
    READ_CONTENT = "read_content"
    UPDATE_CONTENT = "update_content"
    DELETE_CONTENT = "delete_content"
    
    # Question management
    CREATE_QUESTION = "create_question"
    READ_QUESTION = "read_question"
    UPDATE_QUESTION = "update_question"
    DELETE_QUESTION = "delete_question"
    
    # Analytics and reporting
    READ_ANALYTICS = "read_analytics"
    READ_REPORTS = "read_reports"
    
    # System administration
    MANAGE_SYSTEM = "manage_system"
    MANAGE_TOOLS = "manage_tools"
    MANAGE_AGENTS = "manage_agents"
    
    # External API access
    EXTERNAL_API_ACCESS = "external_api_access"


class RolePermissions:
    """Maps roles to their permissions."""
    
    ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
        UserRole.ADMIN: {
            # Admin has all permissions
            Permission.CREATE_USER,
            Permission.READ_USER,
            Permission.UPDATE_USER,
            Permission.DELETE_USER,
            Permission.CREATE_COURSE,
            Permission.READ_COURSE,
            Permission.UPDATE_COURSE,
            Permission.DELETE_COURSE,
            Permission.CREATE_CONTENT,
            Permission.READ_CONTENT,
            Permission.UPDATE_CONTENT,
            Permission.DELETE_CONTENT,
            Permission.CREATE_QUESTION,
            Permission.READ_QUESTION,
            Permission.UPDATE_QUESTION,
            Permission.DELETE_QUESTION,
            Permission.READ_ANALYTICS,
            Permission.READ_REPORTS,
            Permission.MANAGE_SYSTEM,
            Permission.MANAGE_TOOLS,
            Permission.MANAGE_AGENTS,
            Permission.EXTERNAL_API_ACCESS,
        },
        UserRole.TEACHER: {
            # Teachers can manage courses and content
            Permission.READ_USER,
            Permission.CREATE_COURSE,
            Permission.READ_COURSE,
            Permission.UPDATE_COURSE,
            Permission.CREATE_CONTENT,
            Permission.READ_CONTENT,
            Permission.UPDATE_CONTENT,
            Permission.CREATE_QUESTION,
            Permission.READ_QUESTION,
            Permission.UPDATE_QUESTION,
            Permission.READ_ANALYTICS,
            Permission.READ_REPORTS,
            Permission.MANAGE_TOOLS,
            Permission.MANAGE_AGENTS,
        },
        UserRole.STUDENT: {
            # Students can only read content and create questions
            Permission.READ_USER,
            Permission.READ_COURSE,
            Permission.READ_CONTENT,
            Permission.CREATE_QUESTION,
            Permission.READ_QUESTION,
        }
    }
    
    @classmethod
    def get_permissions(cls, role: UserRole) -> Set[Permission]:
        """Get permissions for a specific role."""
        return cls.ROLE_PERMISSIONS.get(role, set())
    
    @classmethod
    def has_permission(cls, role: UserRole, permission: Permission) -> bool:
        """Check if a role has a specific permission."""
        return permission in cls.get_permissions(role)
    
    @classmethod
    def get_roles_with_permission(cls, permission: Permission) -> List[UserRole]:
        """Get all roles that have a specific permission."""
        return [
            role for role, permissions in cls.ROLE_PERMISSIONS.items()
            if permission in permissions
        ]


class User(BaseModel):
    """User model with roles and permissions."""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: Optional[str] = Field(None, description="Username")
    roles: List[UserRole] = Field(default_factory=list, description="User roles")
    permissions: List[Permission] = Field(default_factory=list, description="User permissions")
    is_active: bool = Field(True, description="Whether user is active")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional user metadata")
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_any_role(self, roles: List[UserRole]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        # Check direct permissions first
        if permission in self.permissions:
            return True
        
        # Check role-based permissions
        for role in self.roles:
            if RolePermissions.has_permission(role, permission):
                return True
        
        return False
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(self.has_permission(perm) for perm in permissions)
    
    def get_all_permissions(self) -> Set[Permission]:
        """Get all permissions for this user (role-based + direct)."""
        all_permissions = set(self.permissions)
        for role in self.roles:
            all_permissions.update(RolePermissions.get_permissions(role))
        return all_permissions


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str = Field(..., description="Subject (user ID)")
    email: str = Field(..., description="User email")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    exp: Optional[int] = Field(None, description="Expiration timestamp")
    iat: Optional[int] = Field(None, description="Issued at timestamp")
    iss: Optional[str] = Field(None, description="Issuer")
    aud: Optional[str] = Field(None, description="Audience")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional token metadata")


class APIKeyInfo(BaseModel):
    """API key information model."""
    key_id: str = Field(..., description="API key identifier")
    name: str = Field(..., description="API key name")
    roles: List[UserRole] = Field(default_factory=list, description="Roles associated with this API key")
    permissions: List[Permission] = Field(default_factory=list, description="Direct permissions for this API key")
    is_active: bool = Field(True, description="Whether the API key is active")
    expires_at: Optional[int] = Field(None, description="Expiration timestamp")
    created_at: int = Field(..., description="Creation timestamp")
    last_used_at: Optional[int] = Field(None, description="Last usage timestamp")
    usage_count: int = Field(0, description="Number of times this key has been used")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional API key metadata")


class AccessControlResult(BaseModel):
    """Result of access control check."""
    allowed: bool = Field(..., description="Whether access is allowed")
    reason: Optional[str] = Field(None, description="Reason for denial if not allowed")
    required_roles: List[UserRole] = Field(default_factory=list, description="Required roles")
    required_permissions: List[Permission] = Field(default_factory=list, description="Required permissions")
    user_roles: List[UserRole] = Field(default_factory=list, description="User's roles")
    user_permissions: List[Permission] = Field(default_factory=list, description="User's permissions")

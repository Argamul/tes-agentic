# Role-Based Access Control (RBAC) Documentation

This document provides comprehensive documentation for the Role-Based Access Control (RBAC) system implemented in the FastAPI microservice.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [User Roles](#user-roles)
4. [Permissions](#permissions)
5. [Authentication Methods](#authentication-methods)
6. [Configuration](#configuration)
7. [Usage Examples](#usage-examples)
8. [API Endpoints](#api-endpoints)
9. [Security Considerations](#security-considerations)
10. [Testing](#testing)

## Overview

The RBAC system provides fine-grained access control for API endpoints based on user roles and permissions. It supports:

- **JWT Token Authentication** with external auth service integration
- **API Key Authentication** for external API access
- **Role-based access control** with three main roles: Admin, Teacher, Student
- **Permission-based access control** with granular permissions
- **Automatic route protection** via middleware
- **Flexible configuration** via JSON files and environment variables

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client App    │    │   External Auth  │    │   API Gateway   │
│                 │    │     Service      │    │                 │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                      │                       │
          │ JWT Token            │ Token Verification    │ API Key
          │                      │                       │
          ▼                      ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  RBAC Middleware│  │ API Key         │  │ Rate Limiting   │ │
│  │                 │  │ Middleware      │  │ Middleware      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Auth Dependencies│  │ Route Handlers  │  │ Business Logic  │ │
│  │                 │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## User Roles

### Admin
- **Description**: Full system access with all permissions
- **Use Cases**: System administration, user management, system monitoring
- **Key Permissions**: All permissions including user management, system management, analytics

### Teacher
- **Description**: Educational content and course management
- **Use Cases**: Course creation, content management, student analytics
- **Key Permissions**: Course management, content management, analytics, tool management

### Student
- **Description**: Limited access for learning and content consumption
- **Use Cases**: Course enrollment, content access, question creation
- **Key Permissions**: Read access to courses and content, question creation

## Permissions

### User Management
- `create_user` - Create new users
- `read_user` - View user information
- `update_user` - Modify user data
- `delete_user` - Remove users

### Course Management
- `create_course` - Create new courses
- `read_course` - View course information
- `update_course` - Modify course data
- `delete_course` - Remove courses

### Content Management
- `create_content` - Create educational content
- `read_content` - View content
- `update_content` - Modify content
- `delete_content` - Remove content

### Question Management
- `create_question` - Create questions
- `read_question` - View questions
- `update_question` - Modify questions
- `delete_question` - Remove questions

### Analytics and Reporting
- `read_analytics` - View analytics data
- `read_reports` - Generate and view reports

### System Administration
- `manage_system` - System administration
- `manage_tools` - Tool management
- `manage_agents` - Agent management

### External API Access
- `external_api_access` - Access external API endpoints

## Authentication Methods

### 1. JWT Token Authentication

JWT tokens are verified against an external authentication service.

**Headers Required:**
```
Authorization: Bearer <jwt_token>
```

**Token Payload Structure:**
```json
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
```

### 2. API Key Authentication

API keys are used for external API access with role-based permissions.

**Headers Required:**
```
X-API-Key: <api_key>
```

**API Key Configuration:**
```json
{
  "key": "admin-key-12345",
  "key_id": "admin-001",
  "name": "Admin API Key",
  "roles": ["admin"],
  "permissions": ["external_api_access"],
  "is_active": true,
  "expires_at": null,
  "metadata": {
    "description": "Full admin access API key",
    "path_permissions": {
      "/external/.*": true
    }
  }
}
```

## Configuration

### Environment Variables

```bash
# Auth Service Configuration
AUTH_SERVICE_URL=http://localhost:9000
AUTH_SERVICE_TIMEOUT_SECONDS=5
AUTH_CACHE_ENABLED=true
AUTH_CACHE_TTL_SECONDS=300

# RBAC Configuration
RBAC_CONFIG_FILE=auth/rbac_config.json

# API Key Configuration
EXTERNAL_API_KEYS=admin-key-12345,teacher-key-67890,student-key-11111
EXTERNAL_API_KEYS_FILE=auth/api_keys_config.json
```

### RBAC Configuration File

Create `auth/rbac_config.json`:

```json
{
  "routes": [
    {
      "path_pattern": "^/admin/.*",
      "methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
      "required_roles": ["admin"],
      "allow_anonymous": false
    },
    {
      "path_pattern": "^/teacher/.*",
      "methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
      "required_roles": ["teacher", "admin"],
      "allow_anonymous": false
    },
    {
      "path_pattern": "^/student/.*",
      "methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
      "required_roles": ["student", "teacher", "admin"],
      "allow_anonymous": false
    }
  ]
}
```

### API Keys Configuration File

Create `auth/api_keys_config.json`:

```json
[
  {
    "key": "admin-key-12345",
    "key_id": "admin-001",
    "name": "Admin API Key",
    "roles": ["admin"],
    "permissions": ["external_api_access"],
    "is_active": true,
    "expires_at": null,
    "created_at": 1704067200,
    "metadata": {
      "description": "Full admin access API key",
      "path_permissions": {
        "/external/.*": true
      }
    }
  }
]
```

## Usage Examples

### 1. Basic Route Protection

```python
from auth.dependencies import require_roles, get_current_user
from auth.models import User, UserRole

@app.get("/admin/dashboard")
async def admin_dashboard(user: User = Depends(require_roles(UserRole.ADMIN))):
    return {"message": "Welcome admin", "user": user}
```

### 2. Permission-Based Protection

```python
from auth.dependencies import require_permissions
from auth.models import Permission

@app.post("/courses")
async def create_course(
    course_data: dict,
    user: User = Depends(require_permissions(Permission.CREATE_COURSE))
):
    return {"message": "Course created", "created_by": user.id}
```

### 3. Multiple Role Access

```python
from auth.dependencies import require_teacher_or_admin

@app.get("/teacher/dashboard")
async def teacher_dashboard(user: User = Depends(require_teacher_or_admin)):
    return {"message": "Welcome teacher", "user": user}
```

### 4. Custom Access Control

```python
from auth.dependencies import get_current_user, check_access_control
from auth.models import UserRole, Permission

@app.get("/courses/{course_id}/students")
async def get_course_students(
    course_id: str,
    user: User = Depends(get_current_user)
):
    # Custom logic based on user role
    if UserRole.ADMIN in user.roles:
        # Admin can see all students
        students = get_all_students()
    elif UserRole.TEACHER in user.roles:
        # Teacher can see students in their courses
        students = get_teacher_students(user.id, course_id)
    else:
        # Students can only see other students in the same course
        students = get_course_students(course_id)
    
    return {"course_id": course_id, "students": students}
```

### 5. API Key Authentication

```python
from auth.api_key_middleware import require_api_key_roles

@app.post("/external/llm/generate")
async def external_llm_generate(
    request: TextRequest,
    api_key_user = Depends(require_api_key_roles("admin", "teacher"))
):
    response = await llm_service.generate_text(request.text, request.model)
    return {"response": response, "generated_by": "external_api"}
```

### 6. RBAC Decorator Usage

```python
from auth.rbac_middleware import rbac_protect, admin_only

@rbac_protect(
    path_pattern=".*",
    required_roles=["admin"],
    required_permissions=["manage_system"]
)
@app.get("/system/status")
async def system_status():
    return {"status": "healthy"}

# Or use convenience decorators
@admin_only
@app.get("/admin/users")
async def list_users():
    return {"users": []}
```

## API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|---------|
| GET | `/me` | Get current user profile | Authenticated users |
| GET | `/auth/refresh` | Refresh JWT token | Valid refresh token |
| POST | `/auth/logout` | Logout user | Authenticated users |

### Admin Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|---------|
| GET | `/admin/dashboard` | Admin dashboard | Admin only |
| GET | `/admin/users` | List all users | Admin only |
| POST | `/admin/users` | Create user | Admin only |
| DELETE | `/admin/users/{user_id}` | Delete user | Admin only |
| GET | `/system/status` | System status | Admin only |

### Teacher Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|---------|
| GET | `/teacher/dashboard` | Teacher dashboard | Teacher, Admin |
| GET | `/courses` | List courses | Student, Teacher, Admin |
| POST | `/courses` | Create course | Teacher, Admin |
| PUT | `/courses/{course_id}` | Update course | Teacher, Admin |
| DELETE | `/courses/{course_id}` | Delete course | Admin only |

### Student Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|---------|
| GET | `/student/dashboard` | Student dashboard | Student, Teacher, Admin |
| GET | `/questions` | List questions | Student, Teacher, Admin |
| POST | `/questions` | Create question | Student, Teacher, Admin |

### Analytics Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|---------|
| GET | `/analytics/overview` | Analytics overview | Teacher, Admin |
| GET | `/analytics/courses/{course_id}` | Course analytics | Teacher, Admin |
| GET | `/reports/student-progress` | Student progress report | Teacher, Admin |

### External API Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|---------|
| GET | `/external/status` | External API status | API key required |
| GET | `/external/health` | External API health | API key required |
| POST | `/external/llm/generate` | External LLM generation | API key with admin/teacher role |
| POST | `/external/embedding/generate` | External embedding generation | API key with external_api_access permission |

## Security Considerations

### 1. Token Security
- JWT tokens should be transmitted over HTTPS only
- Implement token expiration and refresh mechanisms
- Use secure token storage on the client side

### 2. API Key Security
- Store API keys securely (environment variables, secret management)
- Implement key rotation policies
- Monitor API key usage and set expiration dates

### 3. Role and Permission Validation
- Always validate roles and permissions on the server side
- Implement principle of least privilege
- Regular audit of user permissions

### 4. Rate Limiting
- Implement rate limiting for authentication endpoints
- Monitor for suspicious activity patterns
- Set appropriate limits for different user roles

### 5. Logging and Monitoring
- Log all authentication attempts and access control decisions
- Monitor for privilege escalation attempts
- Set up alerts for security events

## Testing

### 1. Unit Tests

```python
import pytest
from auth.models import User, UserRole, Permission
from auth.dependencies import check_access_control

def test_user_has_role():
    user = User(
        id="1",
        email="test@example.com",
        roles=[UserRole.ADMIN]
    )
    assert user.has_role(UserRole.ADMIN)
    assert not user.has_role(UserRole.TEACHER)

def test_user_has_permission():
    user = User(
        id="1",
        email="test@example.com",
        roles=[UserRole.ADMIN]
    )
    assert user.has_permission(Permission.CREATE_USER)
    assert user.has_permission(Permission.READ_ANALYTICS)

def test_access_control():
    user = User(
        id="1",
        email="test@example.com",
        roles=[UserRole.TEACHER]
    )
    
    result = check_access_control(
        user=user,
        required_roles=[UserRole.TEACHER, UserRole.ADMIN],
        required_permissions=[Permission.CREATE_COURSE]
    )
    
    assert result.allowed
    assert result.user_roles == [UserRole.TEACHER]
```

### 2. Integration Tests

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_admin_dashboard_access():
    # Test with admin token
    headers = {"Authorization": "Bearer admin_token"}
    response = client.get("/admin/dashboard", headers=headers)
    assert response.status_code == 200
    
    # Test with student token (should fail)
    headers = {"Authorization": "Bearer student_token"}
    response = client.get("/admin/dashboard", headers=headers)
    assert response.status_code == 403

def test_api_key_authentication():
    # Test with valid API key
    headers = {"X-API-Key": "admin-key-12345"}
    response = client.get("/external/status", headers=headers)
    assert response.status_code == 200
    
    # Test with invalid API key
    headers = {"X-API-Key": "invalid-key"}
    response = client.get("/external/status", headers=headers)
    assert response.status_code == 401
```

### 3. Load Testing

```python
import asyncio
import aiohttp

async def test_concurrent_auth():
    """Test concurrent authentication requests."""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(100):
            task = session.get(
                "http://localhost:8000/me",
                headers={"Authorization": "Bearer valid_token"}
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        success_count = sum(1 for r in responses if r.status == 200)
        assert success_count == 100
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Check if JWT token is valid and not expired
   - Verify Authorization header format: `Bearer <token>`
   - Ensure auth service is accessible

2. **403 Forbidden**
   - Verify user has required roles/permissions
   - Check RBAC configuration
   - Review route protection rules

3. **API Key Issues**
   - Verify API key is correct and active
   - Check API key permissions for the endpoint
   - Ensure X-API-Key header is present

4. **Configuration Issues**
   - Verify RBAC config file syntax
   - Check environment variables
   - Review API key configuration

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

This will provide detailed information about authentication and authorization decisions.

## Conclusion

The RBAC system provides a robust, flexible, and secure way to control access to API endpoints. It supports both JWT token authentication and API key authentication, with fine-grained permission control and automatic route protection.

For additional support or questions, please refer to the API documentation at `/docs` or contact the development team.

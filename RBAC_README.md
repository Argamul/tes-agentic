# Role-Based Access Control (RBAC) System

A comprehensive RBAC implementation for FastAPI applications with JWT authentication, API key authentication, and fine-grained permission management.

## 🚀 Features

- **JWT Authentication** with external Auth Service integration
- **API Key Authentication** for external API access
- **Role-Based Access Control** (Admin, Teacher, Student)
- **Permission-Based Access Control** with granular permissions
- **Automatic Route Protection** via middleware
- **Manual Route Protection** via decorators and dependencies
- **Custom Access Control** for complex scenarios
- **Development Mode** with mock authentication
- **Comprehensive Logging** and monitoring
- **Production Ready** with security best practices

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Authentication Methods](#authentication-methods)
- [Access Control](#access-control)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [API Reference](#api-reference)
- [Security](#security)
- [Testing](#testing)
- [Deployment](#deployment)

## 🏃 Quick Start

### 1. Install Dependencies

```bash
pip install fastapi uvicorn httpx python-jose[cryptography] passlib[bcrypt]
```

### 2. Set Environment Variables

```bash
# Copy example environment file
cp env.example .env

# Edit .env file with your configuration
AUTH_SERVICE_URL=https://your-auth-service.com
EXTERNAL_API_KEYS=admin-key-12345,teacher-key-67890
ENVIRONMENT=development
```

### 3. Run the Application

```bash
# Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the System

```bash
# Run the comprehensive test suite
python test_rbac_system.py
```

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│  RBAC Middleware (Automatic Route Protection)              │
├─────────────────────────────────────────────────────────────┤
│  API Key Middleware (External API Protection)              │
├─────────────────────────────────────────────────────────────┤
│  JWT Authentication (User Authentication)                  │
├─────────────────────────────────────────────────────────────┤
│  External Auth Service (Token Verification)                │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
auth/
├── __init__.py
├── auth_service.py          # JWT authentication service
├── api_key_middleware.py    # API key authentication
├── rbac_middleware.py       # RBAC middleware
├── dependencies.py          # FastAPI dependencies
├── models.py               # Data models
├── rbac_config.json        # RBAC configuration
└── api_keys_config.json    # API keys configuration
```

## 🔐 Authentication Methods

### 1. JWT Authentication

JWT tokens are used for user authentication with an external Auth Service.

#### Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "password123"
  }'
```

#### Using JWT Token
```bash
curl -X GET "http://localhost:8000/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 2. API Key Authentication

API keys are used for external API access with role-based permissions.

#### Using API Key
```bash
curl -X GET "http://localhost:8000/external/status" \
  -H "X-API-Key: admin-key-12345"
```

## 🛡️ Access Control

### User Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| **ADMIN** | System administrator | All permissions |
| **TEACHER** | Course instructor | Course/content management, analytics |
| **STUDENT** | Course participant | Read access, create questions |

### Permission System

The system includes granular permissions:

- **User Management**: `create_user`, `read_user`, `update_user`, `delete_user`
- **Course Management**: `create_course`, `read_course`, `update_course`, `delete_course`
- **Content Management**: `create_content`, `read_content`, `update_content`, `delete_content`
- **Question Management**: `create_question`, `read_question`, `update_question`, `delete_question`
- **Analytics**: `read_analytics`, `read_reports`
- **System**: `manage_system`, `manage_tools`, `manage_agents`
- **External API**: `external_api_access`

### Access Control Methods

#### 1. Dependency-Based Protection

```python
from auth.dependencies import require_admin, require_teacher_or_admin, require_permissions

@app.get("/admin-only")
async def admin_endpoint(user: User = Depends(require_admin)):
    return {"message": "Admin only content"}

@app.get("/teacher-content")
async def teacher_endpoint(user: User = Depends(require_teacher_or_admin)):
    return {"message": "Teacher content"}

@app.get("/permission-based")
async def permission_endpoint(user: User = Depends(require_permissions(Permission.CREATE_USER))):
    return {"message": "Permission-based content"}
```

#### 2. Decorator-Based Protection

```python
from auth.rbac_middleware import admin_only, teacher_or_admin

@admin_only
@app.get("/decorator-admin")
async def admin_decorator_endpoint():
    return {"message": "Admin decorator endpoint"}

@teacher_or_admin
@app.get("/decorator-teacher")
async def teacher_decorator_endpoint():
    return {"message": "Teacher decorator endpoint"}
```

#### 3. Custom Access Control

```python
@app.get("/resource/{resource_id}")
async def get_resource(resource_id: str, user: User = Depends(get_current_user)):
    # Custom business logic
    if user.has_role(UserRole.ADMIN):
        access_level = "admin"
    elif user.has_permission(Permission.READ_COURSE):
        access_level = "limited"
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {"resource_id": resource_id, "access_level": access_level}
```

## ⚙️ Configuration

### Environment Variables

```bash
# Auth Service Configuration
AUTH_SERVICE_URL=https://your-auth-service.com
AUTH_SERVICE_TIMEOUT_SECONDS=5
AUTH_CACHE_ENABLED=true
AUTH_CACHE_TTL_SECONDS=300

# API Key Configuration
EXTERNAL_API_KEYS=admin-key-12345,teacher-key-67890,student-key-11111
EXTERNAL_API_KEYS_CONFIG='[{"key":"admin-key-12345","name":"Admin Key","roles":["admin"]}]'
EXTERNAL_API_KEYS_FILE=./auth/api_keys_config.json

# RBAC Configuration
RBAC_CONFIG_FILE=./auth/rbac_config.json

# Environment
ENVIRONMENT=development  # or production
```

### RBAC Configuration

The `auth/rbac_config.json` file defines automatic route protection:

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
    }
  ]
}
```

### API Keys Configuration

The `auth/api_keys_config.json` file defines API keys:

```json
[
  {
    "key": "admin-key-12345",
    "key_id": "admin-001",
    "name": "Admin API Key",
    "roles": ["admin"],
    "permissions": ["external_api_access", "create_user"],
    "is_active": true,
    "expires_at": null,
    "metadata": {
      "description": "Full admin access API key",
      "path_permissions": {
        "/external/.*": true
      }
    }
  }
]
```

## 📚 Usage Examples

### Basic Authentication

```python
from auth.dependencies import get_current_user, get_current_user_optional

@app.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    return {"user_id": user.id, "email": user.email}

@app.get("/public")
async def public_endpoint(user: Optional[User] = Depends(get_current_user_optional)):
    if user:
        return {"message": f"Hello {user.email}"}
    return {"message": "Hello anonymous user"}
```

### Role-Based Access

```python
from auth.dependencies import require_admin, require_teacher_or_admin, require_student_or_above

@app.get("/admin/dashboard")
async def admin_dashboard(user: User = Depends(require_admin)):
    return {"message": "Admin dashboard", "user": user.email}

@app.get("/teacher/courses")
async def teacher_courses(user: User = Depends(require_teacher_or_admin)):
    return {"message": "Teacher courses", "user": user.email}

@app.get("/student/assignments")
async def student_assignments(user: User = Depends(require_student_or_above)):
    return {"message": "Student assignments", "user": user.email}
```

### Permission-Based Access

```python
from auth.dependencies import require_permissions, require_all_permissions
from auth.models import Permission

@app.get("/users")
async def list_users(user: User = Depends(require_permissions(Permission.READ_USER))):
    return {"users": ["user1", "user2"]}

@app.get("/admin/users")
async def admin_users(user: User = Depends(require_all_permissions(
    Permission.CREATE_USER,
    Permission.UPDATE_USER,
    Permission.DELETE_USER
))):
    return {"message": "Full user management access"}
```

### API Key Authentication

```python
from auth.api_key_middleware import get_api_key_user, require_api_key_roles

@app.get("/external/status")
async def external_status(api_key_user = Depends(get_api_key_user)):
    return {"status": "ok", "api_key": api_key_user.key_id}

@app.get("/external/admin")
async def external_admin(api_key_user = Depends(require_api_key_roles("admin"))):
    return {"message": "Admin external endpoint"}
```

### Custom Access Control

```python
@app.get("/courses/{course_id}")
async def get_course(course_id: str, user: User = Depends(get_current_user)):
    # Custom business logic
    if user.has_role(UserRole.ADMIN):
        # Admin can see all courses
        course_data = get_full_course_data(course_id)
    elif user.has_role(UserRole.TEACHER):
        # Teacher can see courses they teach
        if is_course_instructor(course_id, user.id):
            course_data = get_teacher_course_data(course_id)
        else:
            raise HTTPException(status_code=403, detail="Not your course")
    else:
        # Student can see courses they're enrolled in
        if is_course_student(course_id, user.id):
            course_data = get_student_course_data(course_id)
        else:
            raise HTTPException(status_code=403, detail="Not enrolled")
    
    return {"course": course_data}
```

## 📖 API Reference

### Dependencies

#### Authentication Dependencies

- `get_current_user()` - Get current authenticated user (raises 401 if not authenticated)
- `get_current_user_optional()` - Get current user if authenticated, otherwise None

#### Role-Based Dependencies

- `require_admin` - Require admin role
- `require_teacher_or_admin` - Require teacher or admin role
- `require_student_or_above` - Require student, teacher, or admin role
- `require_roles(*roles)` - Require any of the specified roles

#### Permission-Based Dependencies

- `require_permissions(*permissions)` - Require any of the specified permissions
- `require_all_permissions(*permissions)` - Require all specified permissions
- `require_user_management` - Require user management permissions
- `require_course_management` - Require course management permissions
- `require_content_management` - Require content management permissions
- `require_system_management` - Require system management permissions
- `require_analytics_access` - Require analytics access permissions

#### API Key Dependencies

- `get_api_key_user` - Get API key user info
- `require_api_key_roles(*roles)` - Require API key with specified roles
- `require_api_key_permissions(*permissions)` - Require API key with specified permissions

### Decorators

#### RBAC Decorators

- `@admin_only` - Admin-only access
- `@teacher_or_admin` - Teacher or admin access
- `@student_or_above` - Student or above access
- `@rbac_protect(...)` - Custom RBAC protection

### Models

#### User Model

```python
class User(BaseModel):
    id: str
    email: str
    username: Optional[str]
    roles: List[UserRole]
    permissions: List[Permission]
    is_active: bool
    metadata: Dict[str, Any]
    
    def has_role(self, role: UserRole) -> bool
    def has_any_role(self, roles: List[UserRole]) -> bool
    def has_permission(self, permission: Permission) -> bool
    def has_any_permission(self, permissions: List[Permission]) -> bool
    def get_all_permissions(self) -> Set[Permission]
```

#### UserRole Enum

```python
class UserRole(str, Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
```

#### Permission Enum

```python
class Permission(str, Enum):
    CREATE_USER = "create_user"
    READ_USER = "read_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    # ... more permissions
```

## 🔒 Security

### Security Features

1. **Token Validation**
   - JWT structure validation
   - Token expiration checking
   - External service verification
   - Token caching for performance

2. **API Key Security**
   - Secure key generation
   - Expiration support
   - Usage tracking
   - Path-specific permissions

3. **Access Control**
   - Role-based access
   - Permission-based access
   - Custom access checks
   - Resource ownership validation

4. **Middleware Protection**
   - Automatic route protection
   - Configurable access rules
   - Anonymous access support
   - Detailed error responses

### Security Best Practices

1. **Use HTTPS in production**
2. **Implement token refresh**
3. **Set appropriate expiration times**
4. **Monitor token usage**
5. **Rotate API keys regularly**
6. **Use least privilege principle**
7. **Never log sensitive tokens**
8. **Use secure key storage**
9. **Implement rate limiting**
10. **Monitor access patterns**

## 🧪 Testing

### Running Tests

```bash
# Run the comprehensive test suite
python test_rbac_system.py

# Run with custom API URL
API_BASE_URL=http://localhost:8000 python test_rbac_system.py
```

### Test Coverage

The test suite covers:

- Health check endpoints
- JWT authentication flow
- Role-based access control
- Permission-based access control
- API key authentication
- External API access
- Unauthorized access scenarios
- Custom access control
- Error handling

### Writing Custom Tests

```python
import pytest
from fastapi.testclient import TestClient
from auth.models import User, UserRole, Permission

def test_admin_access():
    user = User(id="1", email="admin@test.com", roles=[UserRole.ADMIN])
    assert user.has_role(UserRole.ADMIN)
    assert user.has_permission(Permission.CREATE_USER)

def test_teacher_permissions():
    user = User(id="2", email="teacher@test.com", roles=[UserRole.TEACHER])
    assert user.has_permission(Permission.CREATE_COURSE)
    assert not user.has_permission(Permission.DELETE_USER)

@pytest.mark.asyncio
async def test_jwt_auth():
    response = await client.get("/me", headers={"Authorization": "Bearer valid_token"})
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_api_key_auth():
    response = await client.get("/external/status", headers={"X-API-Key": "valid_key"})
    assert response.status_code == 200
```

## 🚀 Deployment

### Production Configuration

```bash
# Production environment variables
ENVIRONMENT=production
AUTH_SERVICE_URL=https://auth.yourdomain.com
AUTH_CACHE_ENABLED=true
AUTH_CACHE_TTL_SECONDS=300

# Use secure API keys
EXTERNAL_API_KEYS_FILE=/secure/path/api_keys.json
RBAC_CONFIG_FILE=/secure/path/rbac_config.json
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rbac-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rbac-app
  template:
    metadata:
      labels:
        app: rbac-app
    spec:
      containers:
      - name: rbac-app
        image: your-registry/rbac-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: AUTH_SERVICE_URL
          value: "https://auth.yourdomain.com"
```

### Monitoring

Monitor the following metrics:

- Authentication success/failure rates
- Authorization success/failure rates
- API key usage patterns
- Token expiration patterns
- Access control violations
- Performance metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

1. Check the documentation
2. Run the test suite
3. Check the logs for errors
4. Create an issue with detailed information

## 🔄 Changelog

### Version 1.0.0
- Initial release
- JWT authentication with external service
- API key authentication
- Role-based access control
- Permission-based access control
- Comprehensive middleware
- Development mode support
- Full test suite

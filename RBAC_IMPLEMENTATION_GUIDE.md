# RBAC Implementation Guide

## Overview

Your FastAPI application has a comprehensive Role-Based Access Control (RBAC) system with the following features:

- **JWT Token Authentication** with external Auth Service integration
- **API Key Authentication** middleware for external API calls
- **Role-based access control** for endpoints (admin, teacher, student)
- **Permission-based access control** with fine-grained permissions
- **Automatic route protection** via middleware
- **Manual route protection** via decorators and dependencies

## Architecture

### 1. Authentication Layers

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

### 2. User Roles

- **ADMIN**: Full system access, user management, system administration
- **TEACHER**: Course and content management, analytics access
- **STUDENT**: Read access to courses/content, can create questions

### 3. Permission System

The system includes granular permissions for:
- User management (create, read, update, delete)
- Course management (create, read, update, delete)
- Content management (create, read, update, delete)
- Question management (create, read, update, delete)
- Analytics and reporting
- System administration
- External API access

## Usage Examples

### 1. JWT Authentication

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

#### Using API Key
```bash
curl -X GET "http://localhost:8000/external/status" \
  -H "X-API-Key: admin-key-12345"
```

### 3. Role-Based Access Examples

#### Admin Only Endpoints
```bash
# Admin dashboard
curl -X GET "http://localhost:8000/admin/dashboard" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"

# List all users
curl -X GET "http://localhost:8000/admin/users" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"

# Create new user
curl -X POST "http://localhost:8000/admin/users" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com", "role": "student"}'
```

#### Teacher and Admin Endpoints
```bash
# Teacher dashboard
curl -X GET "http://localhost:8000/teacher/dashboard" \
  -H "Authorization: Bearer TEACHER_JWT_TOKEN"

# Create course
curl -X POST "http://localhost:8000/courses" \
  -H "Authorization: Bearer TEACHER_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Mathematics 101", "description": "Basic math course"}'

# Analytics overview
curl -X GET "http://localhost:8000/analytics/overview" \
  -H "Authorization: Bearer TEACHER_JWT_TOKEN"
```

#### Student and Above Endpoints
```bash
# Student dashboard
curl -X GET "http://localhost:8000/student/dashboard" \
  -H "Authorization: Bearer STUDENT_JWT_TOKEN"

# List courses
curl -X GET "http://localhost:8000/courses" \
  -H "Authorization: Bearer STUDENT_JWT_TOKEN"

# Create question
curl -X POST "http://localhost:8000/questions" \
  -H "Authorization: Bearer STUDENT_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the derivative of x²?", "type": "math"}'
```

### 4. External API Access

#### Using Admin API Key
```bash
# LLM generation
curl -X POST "http://localhost:8000/external/llm/generate" \
  -H "X-API-Key: admin-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, world!", "model": "gpt-3.5-turbo"}'

# Embedding generation
curl -X POST "http://localhost:8000/external/embedding/generate" \
  -H "X-API-Key: admin-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"text": "Sample text", "model": "all-MiniLM-L6-v2"}'
```

#### Using Teacher API Key
```bash
# Teacher can access LLM and embedding endpoints
curl -X POST "http://localhost:8000/external/llm/generate" \
  -H "X-API-Key: teacher-key-67890" \
  -H "Content-Type: application/json" \
  -d '{"text": "Generate a math problem", "model": "gpt-3.5-turbo"}'
```

#### Using Student API Key
```bash
# Student can only access status endpoints
curl -X GET "http://localhost:8000/external/status" \
  -H "X-API-Key: student-key-11111"

curl -X GET "http://localhost:8000/external/health" \
  -H "X-API-Key: student-key-11111"
```

## Configuration

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

### RBAC Configuration File

The `auth/rbac_config.json` file defines automatic route protection rules:

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

The `auth/api_keys_config.json` file defines API keys with their roles and permissions:

```json
[
  {
    "key": "admin-key-12345",
    "key_id": "admin-001",
    "name": "Admin API Key",
    "roles": ["admin"],
    "permissions": ["external_api_access", "create_user", "read_user"],
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

## Development Mode

In development mode (when `ENVIRONMENT=development`), the system provides:

1. **Mock JWT tokens** for testing
2. **Mock user data** for authentication
3. **Simplified auth service** integration

### Development Login Response
```json
{
  "access_token": "mock-access-token-12345",
  "refresh_token": "mock-refresh-token-67890",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "dev-user-123",
    "email": "dev@example.com",
    "username": "devuser",
    "roles": ["admin"],
    "permissions": ["external_api_access"],
    "is_active": true
  }
}
```

## Security Features

### 1. Token Validation
- JWT structure validation
- Token expiration checking
- External service verification
- Token caching for performance

### 2. API Key Security
- Secure key generation
- Expiration support
- Usage tracking
- Path-specific permissions

### 3. Access Control
- Role-based access
- Permission-based access
- Custom access checks
- Resource ownership validation

### 4. Middleware Protection
- Automatic route protection
- Configurable access rules
- Anonymous access support
- Detailed error responses

## Error Handling

### Authentication Errors
```json
{
  "detail": "Missing or invalid Authorization header"
}
```

### Authorization Errors
```json
{
  "detail": "Insufficient role. Required: ['admin'], User has: ['student']",
  "required_roles": ["admin"],
  "required_permissions": [],
  "user_roles": ["student"],
  "user_permissions": ["read_course", "read_content"]
}
```

### API Key Errors
```json
{
  "detail": "Invalid or expired API key"
}
```

## Best Practices

### 1. Token Management
- Use HTTPS in production
- Implement token refresh
- Set appropriate expiration times
- Monitor token usage

### 2. API Key Management
- Rotate keys regularly
- Use least privilege principle
- Monitor key usage
- Implement key expiration

### 3. Access Control
- Use role-based access for broad permissions
- Use permission-based access for fine-grained control
- Implement custom checks for complex scenarios
- Validate resource ownership

### 4. Security
- Never log sensitive tokens
- Use secure key storage
- Implement rate limiting
- Monitor access patterns

## Testing

### Unit Tests
```python
# Test role-based access
def test_admin_access():
    user = User(id="1", email="admin@test.com", roles=[UserRole.ADMIN])
    assert user.has_role(UserRole.ADMIN)
    assert user.has_permission(Permission.CREATE_USER)

# Test permission-based access
def test_teacher_permissions():
    user = User(id="2", email="teacher@test.com", roles=[UserRole.TEACHER])
    assert user.has_permission(Permission.CREATE_COURSE)
    assert not user.has_permission(Permission.DELETE_USER)
```

### Integration Tests
```python
# Test JWT authentication
async def test_jwt_auth():
    response = await client.get("/me", headers={"Authorization": "Bearer valid_token"})
    assert response.status_code == 200

# Test API key authentication
async def test_api_key_auth():
    response = await client.get("/external/status", headers={"X-API-Key": "valid_key"})
    assert response.status_code == 200
```

## Monitoring and Logging

The system includes comprehensive logging for:
- Authentication attempts
- Authorization decisions
- API key usage
- Access control violations
- Token validation results

Monitor these logs for:
- Failed authentication attempts
- Unauthorized access attempts
- API key abuse
- Token expiration patterns
- Performance issues

## Conclusion

Your RBAC system provides a robust, scalable, and secure authentication and authorization solution. It supports both user-based JWT authentication and API key authentication, with comprehensive role and permission management. The system is production-ready with proper error handling, logging, and security features.

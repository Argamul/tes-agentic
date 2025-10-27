# Role-Based Access Control (RBAC) Usage Examples

This document provides comprehensive examples of how to use the RBAC system in the NLP/AI Microservice.

## Table of Contents

1. [Authentication Methods](#authentication-methods)
2. [Role-Based Access Control](#role-based-access-control)
3. [Permission-Based Access Control](#permission-based-access-control)
4. [API Key Authentication](#api-key-authentication)
5. [Protected Route Examples](#protected-route-examples)
6. [Advanced RBAC Patterns](#advanced-rbac-patterns)
7. [Configuration Examples](#configuration-examples)
8. [Testing and Development](#testing-and-development)

## Authentication Methods

### 1. JWT Token Authentication

The service supports JWT token authentication with an external Auth Service.

#### Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "username": "johndoe",
    "roles": ["teacher"],
    "permissions": ["create_course", "read_course"],
    "is_active": true
  }
}
```

#### Using JWT Token
```bash
curl -X GET "http://localhost:8000/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Refresh Token
```bash
curl -X GET "http://localhost:8000/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

#### Logout
```bash
curl -X POST "http://localhost:8000/auth/logout" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 2. API Key Authentication

For external API access, use API key authentication.

```bash
curl -X GET "http://localhost:8000/external/status" \
  -H "X-API-Key: admin-key-12345"
```

## Role-Based Access Control

### User Roles

The system supports three main roles:

- **Admin**: Full system access
- **Teacher**: Educational content and course management
- **Student**: Limited access for learning and content consumption

### Role Hierarchy

```
Admin > Teacher > Student
```

Higher roles inherit permissions from lower roles.

### Example: Admin-Only Endpoint

```python
@app.get("/admin/dashboard")
async def admin_dashboard(user: User = Depends(require_admin)):
    """Admin dashboard with system overview."""
    return {
        "message": "Welcome to admin dashboard",
        "user": {
            "id": user.id,
            "email": user.email,
            "roles": [role.value for role in user.roles]
        }
    }
```

**Usage:**
```bash
curl -X GET "http://localhost:8000/admin/dashboard" \
  -H "Authorization: Bearer <admin-token>"
```

### Example: Teacher and Admin Access

```python
@app.get("/teacher/dashboard")
async def teacher_dashboard(user: User = Depends(require_teacher_or_admin)):
    """Teacher dashboard with course management."""
    return {
        "message": "Welcome to teacher dashboard",
        "user": {
            "id": user.id,
            "email": user.email,
            "roles": [role.value for role in user.roles]
        }
    }
```

**Usage:**
```bash
curl -X GET "http://localhost:8000/teacher/dashboard" \
  -H "Authorization: Bearer <teacher-token>"
```

### Example: Student and Above Access

```python
@app.get("/student/dashboard")
async def student_dashboard(user: User = Depends(require_student_or_above)):
    """Student dashboard with enrolled courses."""
    return {
        "message": "Welcome to student dashboard",
        "user": {
            "id": user.id,
            "email": user.email,
            "roles": [role.value for role in user.roles]
        }
    }
```

**Usage:**
```bash
curl -X GET "http://localhost:8000/student/dashboard" \
  -H "Authorization: Bearer <student-token>"
```

## Permission-Based Access Control

### Available Permissions

- **User Management**: `create_user`, `read_user`, `update_user`, `delete_user`
- **Course Management**: `create_course`, `read_course`, `update_course`, `delete_course`
- **Content Management**: `create_content`, `read_content`, `update_content`, `delete_content`
- **Question Management**: `create_question`, `read_question`, `update_question`, `delete_question`
- **Analytics**: `read_analytics`, `read_reports`
- **System Administration**: `manage_system`, `manage_tools`, `manage_agents`
- **External API**: `external_api_access`

### Example: Single Permission Required

```python
@app.post("/courses")
async def create_course(
    course_data: dict,
    user: User = Depends(require_permissions(Permission.CREATE_COURSE))
):
    """Create a new course - requires course creation permission."""
    return {
        "message": "Course created successfully",
        "course_id": "new-course-123",
        "created_by": user.id
    }
```

**Usage:**
```bash
curl -X POST "http://localhost:8000/courses" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mathematics 101",
    "description": "Introduction to mathematics"
  }'
```

### Example: Multiple Permissions (ANY)

```python
@app.get("/analytics/overview")
async def analytics_overview(user: User = Depends(require_analytics_access)):
    """Get analytics overview - requires analytics or reports permission."""
    return {
        "total_students": 1250,
        "total_courses": 45,
        "completion_rate": "78%"
    }
```

### Example: Multiple Permissions (ALL)

```python
@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_user: User = Depends(require_all_permissions(Permission.DELETE_USER))
):
    """Delete a user - requires delete user permission."""
    return {
        "message": f"User {user_id} deleted successfully",
        "deleted_by": admin_user.id
    }
```

## API Key Authentication

### API Key Configuration

API keys are configured in `auth/api_keys_config.json`:

```json
[
  {
    "key": "admin-key-12345",
    "key_id": "admin-001",
    "name": "Admin API Key",
    "roles": ["admin"],
    "permissions": [
      "external_api_access",
      "create_user",
      "read_user"
    ],
    "is_active": true,
    "expires_at": null,
    "metadata": {
      "description": "Full admin access API key",
      "department": "engineering"
    }
  }
]
```

### Example: External API with Admin Role

```bash
curl -X POST "http://localhost:8000/external/llm/generate" \
  -H "X-API-Key: admin-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Explain quantum computing",
    "model": "gpt-3.5-turbo"
  }'
```

### Example: External API with Teacher Role

```bash
curl -X POST "http://localhost:8000/external/embedding/generate" \
  -H "X-API-Key: teacher-key-67890" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Sample text for embedding",
    "model": "all-MiniLM-L6-v2"
  }'
```

## Protected Route Examples

### 1. Basic Role Protection

```python
@app.get("/courses")
async def list_courses(user: User = Depends(require_student_or_above)):
    """List all courses - students, teachers, admins."""
    return {
        "courses": [
            {"id": "1", "name": "Mathematics 101", "instructor": "Dr. Smith"},
            {"id": "2", "name": "Physics 201", "instructor": "Dr. Johnson"}
        ]
    }
```

### 2. Permission-Based Protection

```python
@app.post("/content")
async def create_content(
    content_data: dict,
    user: User = Depends(require_content_management)
):
    """Create new content - teachers and admins."""
    return {
        "message": "Content created successfully",
        "content_id": "new-content-123",
        "created_by": user.id
    }
```

### 3. Custom Access Control Logic

```python
@app.get("/courses/{course_id}/students")
async def get_course_students(
    course_id: str,
    user: User = Depends(get_current_user)
):
    """Get students in a course with custom access control."""
    if UserRole.ADMIN in user.roles:
        # Admin can see all students
        students = get_all_students(course_id)
    elif UserRole.TEACHER in user.roles:
        # Teacher can only see students in their courses
        students = get_course_students_for_teacher(course_id, user.id)
    else:
        # Students can only see other students in the same course
        students = get_fellow_students(course_id, user.id)
    
    return {
        "course_id": course_id,
        "students": students,
        "requested_by": user.id
    }
```

## Advanced RBAC Patterns

### 1. Resource Ownership

```python
@app.get("/my-courses")
async def get_my_courses(user: User = Depends(get_current_user)):
    """Get courses based on user's role and ownership."""
    if user.has_role(UserRole.ADMIN):
        # Admins see all courses
        courses = get_all_courses()
        relationship = "admin"
    elif user.has_role(UserRole.TEACHER):
        # Teachers see courses they instruct
        courses = get_courses_by_instructor(user.id)
        relationship = "instructor"
    else:
        # Students see courses they're enrolled in
        courses = get_courses_by_student(user.id)
        relationship = "student"
    
    return {
        "courses": courses,
        "relationship": relationship,
        "user_id": user.id
    }
```

### 2. Permission-Based Feature Flags

```python
@app.get("/features")
async def get_available_features(user: User = Depends(get_current_user)):
    """Get available features based on user's permissions."""
    all_features = {
        "advanced_analytics": {
            "name": "Advanced Analytics",
            "required_permission": Permission.READ_ANALYTICS.value
        },
        "user_management": {
            "name": "User Management",
            "required_permission": Permission.CREATE_USER.value
        }
    }
    
    # Filter features based on user's permissions
    available_features = {}
    for feature_key, feature_info in all_features.items():
        required_perm = Permission(feature_info["required_permission"])
        if user.has_permission(required_perm):
            available_features[feature_key] = feature_info
    
    return {
        "available_features": available_features,
        "user_permissions": [perm.value for perm in user.get_all_permissions()]
    }
```

### 3. Role-Based Data Filtering

```python
@app.get("/assignments")
async def list_assignments(user: User = Depends(require_student_or_above)):
    """List assignments with role-based filtering."""
    if user.has_role(UserRole.ADMIN):
        # Admins see all assignments
        assignments = get_all_assignments()
    elif user.has_role(UserRole.TEACHER):
        # Teachers see assignments from their courses
        assignments = get_assignments_by_teacher(user.id)
    else:
        # Students see only their assignments
        assignments = get_assignments_by_student(user.id)
    
    return {
        "assignments": assignments,
        "total": len(assignments),
        "requested_by": user.id
    }
```

## Configuration Examples

### Environment Variables

```bash
# Auth Service Configuration
AUTH_SERVICE_URL=http://localhost:9000
AUTH_SERVICE_TIMEOUT_SECONDS=5
AUTH_CACHE_ENABLED=true
AUTH_CACHE_TTL_SECONDS=300

# RBAC Configuration
RBAC_CONFIG_FILE=auth/rbac_config.json

# API Keys Configuration
EXTERNAL_API_KEYS=admin-key-12345,teacher-key-67890
EXTERNAL_API_KEYS_FILE=auth/api_keys_config.json

# Environment
ENVIRONMENT=development
```

### RBAC Configuration File

```json
{
  "routes": [
    {
      "path_pattern": "^/admin/.*",
      "methods": ["GET", "POST", "PUT", "DELETE"],
      "required_roles": ["admin"],
      "allow_anonymous": false
    },
    {
      "path_pattern": "^/teacher/.*",
      "methods": ["GET", "POST", "PUT", "DELETE"],
      "required_roles": ["teacher", "admin"],
      "allow_anonymous": false
    },
    {
      "path_pattern": "^/student/.*",
      "methods": ["GET", "POST", "PUT", "DELETE"],
      "required_roles": ["student", "teacher", "admin"],
      "allow_anonymous": false
    }
  ]
}
```

## Testing and Development

### Development Mode

In development mode, the service provides mock authentication:

```bash
export ENVIRONMENT=development
```

This allows testing without a real auth service.

### Test Authentication

```python
# Test with mock token
curl -X GET "http://localhost:8000/me" \
  -H "Authorization: Bearer mock-token-123"
```

### API Key Testing

```bash
# Test with configured API key
curl -X GET "http://localhost:8000/external/status" \
  -H "X-API-Key: admin-key-12345"
```

### Error Handling Examples

#### Missing Token
```bash
curl -X GET "http://localhost:8000/admin/dashboard"
# Response: 401 Unauthorized
{
  "detail": "Missing or invalid Authorization header"
}
```

#### Insufficient Role
```bash
curl -X GET "http://localhost:8000/admin/dashboard" \
  -H "Authorization: Bearer <student-token>"
# Response: 403 Forbidden
{
  "detail": "Insufficient role. Required: ['admin'], User has: ['student']"
}
```

#### Invalid API Key
```bash
curl -X GET "http://localhost:8000/external/status" \
  -H "X-API-Key: invalid-key"
# Response: 401 Unauthorized
{
  "detail": "Invalid or expired API key"
}
```

## Best Practices

1. **Use Role-Based Access for Broad Categories**: Use roles for general access levels (admin, teacher, student).

2. **Use Permissions for Specific Actions**: Use permissions for granular control over specific operations.

3. **Combine Roles and Permissions**: Use both roles and permissions together for maximum flexibility.

4. **Implement Resource Ownership**: Check ownership of resources in addition to roles/permissions.

5. **Log Access Attempts**: The system logs all authentication and authorization attempts for security monitoring.

6. **Use HTTPS in Production**: Always use HTTPS when transmitting tokens and API keys.

7. **Rotate API Keys Regularly**: Implement a process for regular API key rotation.

8. **Monitor Usage**: Track API key usage and user activity for security and billing purposes.

## Troubleshooting

### Common Issues

1. **Auth Service Not Configured**: Ensure `AUTH_SERVICE_URL` is set correctly.

2. **Token Expired**: Check token expiration and use refresh tokens appropriately.

3. **Invalid API Key**: Verify API key configuration and expiration.

4. **Permission Denied**: Check user roles and permissions against endpoint requirements.

5. **Cache Issues**: Clear auth cache if experiencing stale authentication issues.

### Debug Logging

Enable debug logging to troubleshoot authentication issues:

```bash
export LOG_LEVEL=DEBUG
```

This will provide detailed logs of authentication and authorization decisions.

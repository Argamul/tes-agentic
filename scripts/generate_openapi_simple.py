#!/usr/bin/env python3
"""
Generate OpenAPI Documentation for NLP/AI Microservice (Simple Version)

This script generates comprehensive OpenAPI documentation without requiring
full application initialization to avoid dependency issues.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openapi_schema import get_openapi_schema, APIExamples


def generate_openapi_json() -> Dict[str, Any]:
    """Generate OpenAPI JSON schema"""
    print("Generating OpenAPI JSON schema...")
    
    # Get the base schema
    openapi_schema = get_openapi_schema()
    
    # Add comprehensive paths
    openapi_schema["paths"] = {
        "/health": {
            "get": {
                "tags": ["health"],
                "summary": "Health check endpoint",
                "description": "Health check endpoint to verify service status.",
                "responses": {
                    "200": {
                        "description": "Service is healthy",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HealthResponse"},
                                "example": {"status": "healthy", "service": "nlp-ai-microservice"}
                            }
                        }
                    }
                }
            }
        },
        "/llm/generate": {
            "post": {
                "tags": ["llm"],
                "summary": "Generate text using Large Language Models",
                "description": "Supports multiple LLM providers including OpenAI GPT, Anthropic Claude, and local LLaMA models.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/TextRequest"},
                            "example": {
                                "text": "Explain how to solve this SAT math problem: If 2x + 3y = 12 and x - y = 1, what is the value of x?",
                                "model": "gpt-3.5-turbo"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Generated text response",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/TextResponse"},
                                "example": {"response": "To solve this system of equations, we can use substitution or elimination..."}
                            }
                        }
                    },
                    "500": {
                        "description": "Internal server error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/llm/chat": {
            "post": {
                "tags": ["llm"],
                "summary": "Chat completion using Large Language Models",
                "description": "Provides conversational AI capabilities for interactive tutoring and Q&A sessions.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/TextRequest"},
                            "example": {
                                "text": "Help me understand this UTBK physics problem: Sebuah benda bermassa 2 kg bergerak dengan kecepatan 5 m/s. Berapakah momentum benda tersebut?",
                                "model": "gpt-3.5-turbo"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Chat response",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/TextResponse"},
                                "example": {"response": "Momentum adalah besaran fisika yang didefinisikan sebagai hasil kali massa dan kecepatan..."}
                            }
                        }
                    }
                }
            }
        },
        "/embedding/generate": {
            "post": {
                "tags": ["embeddings"],
                "summary": "Generate text embeddings for vector operations",
                "description": "Converts text into high-dimensional vectors for similarity search and semantic analysis.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/EmbeddingRequest"},
                            "example": {
                                "text": "SAT math problem about quadratic equations",
                                "model": "all-MiniLM-L6-v2"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Generated embedding vector",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/EmbeddingResponse"},
                                "example": {"embedding": [0.1, 0.2, 0.3, 0.4, 0.5]}
                            }
                        }
                    }
                }
            }
        },
        "/embedding/batch": {
            "post": {
                "tags": ["embeddings"],
                "summary": "Generate embeddings for multiple texts in batch",
                "description": "Efficiently processes multiple texts at once for better performance.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/EmbeddingRequest"}
                            },
                            "example": [
                                {"text": "SAT math problem 1", "model": "all-MiniLM-L6-v2"},
                                {"text": "SAT math problem 2", "model": "all-MiniLM-L6-v2"}
                            ]
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Generated embedding vectors",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/BatchEmbeddingResponse"},
                                "example": {"embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]}
                            }
                        }
                    }
                }
            }
        },
        "/search/hybrid": {
            "post": {
                "tags": ["hybrid-search"],
                "summary": "Perform hybrid search combining BM25 and semantic search",
                "description": "Combines keyword-based search (BM25) with semantic similarity search for optimal results.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/HybridSearchRequest"},
                            "example": {
                                "query": "SAT math problems about algebra",
                                "top_k": 10,
                                "alpha": 0.6,
                                "filter": {"type": "question", "subject": "math"}
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Hybrid search results",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HybridSearchResponse"},
                                "example": {
                                    "results": [
                                        {
                                            "id": "1",
                                            "document": "SAT math problem about algebra",
                                            "score": 0.95,
                                            "bm25_score": 0.9,
                                            "semantic_score": 0.8,
                                            "metadata": {"type": "question", "subject": "math"}
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        },
        "/search/questions": {
            "post": {
                "tags": ["hybrid-search"],
                "summary": "Search specifically for questions in the educational database",
                "description": "Filters search results to only include content marked as questions.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/HybridSearchRequest"},
                            "example": {
                                "query": "quadratic equations",
                                "top_k": 5,
                                "alpha": 0.7
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Question search results",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HybridSearchResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/search/materials": {
            "post": {
                "tags": ["hybrid-search"],
                "summary": "Search specifically for educational materials and study guides",
                "description": "Filters search results to only include content marked as materials.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/HybridSearchRequest"},
                            "example": {
                                "query": "physics formulas",
                                "top_k": 3,
                                "alpha": 0.5
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Material search results",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HybridSearchResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/ingest": {
            "post": {
                "tags": ["vector-search"],
                "summary": "Ingest documents into the vector database for search",
                "description": "Adds documents to both BM25 (Elasticsearch) and semantic (Qdrant) search indexes.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/IngestRequest"},
                            "example": {
                                "texts": [
                                    "If 2x + 3y = 12 and x - y = 1, what is the value of x?",
                                    "What is the area of a circle with radius 5?"
                                ],
                                "metadata_list": [
                                    {"type": "question", "subject": "math", "test_type": "SAT"},
                                    {"type": "question", "subject": "geometry", "test_type": "SAT"}
                                ]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Document ingestion results",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/IngestResponse"},
                                "example": {
                                    "elastic_ids": ["doc_1", "doc_2"],
                                    "qdrant_ids": ["qdrant_1", "qdrant_2"]
                                }
                            }
                        }
                    }
                }
            }
        },
        "/agent/execute": {
            "post": {
                "tags": ["agents"],
                "summary": "Execute AI agent with tool integration",
                "description": "Runs an AI agent that can use various tools to solve complex problems.",
                "security": [{"BearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/AgentRequest"},
                            "example": {
                                "query": "Calculate the derivative of x² + 3x - 2 and explain the steps",
                                "tools": ["calculator", "math"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Agent execution result",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AgentResponse"},
                                "example": {"result": "I'll help you solve this step by step using the calculator tool..."}
                            }
                        }
                    }
                }
            }
        },
        "/tools/list": {
            "get": {
                "tags": ["tools"],
                "summary": "List available tools for AI agents",
                "description": "Returns a list of all available tools that can be used by AI agents.",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {
                        "description": "List of available tools",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "tools": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "name": {"type": "string"},
                                                    "description": {"type": "string"}
                                                }
                                            }
                                        }
                                    }
                                },
                                "example": {
                                    "tools": [
                                        {"name": "calculator", "description": "Mathematical calculations"},
                                        {"name": "text_analysis", "description": "Text metrics and analysis"}
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        },
        "/auth/login": {
            "post": {
                "tags": ["authentication"],
                "summary": "User login endpoint",
                "description": "Authenticates users and returns JWT tokens for API access.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/LoginRequest"},
                            "example": {
                                "email": "student@example.com",
                                "password": "securepassword123"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Login successful",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/LoginResponse"},
                                "example": {
                                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                    "token_type": "bearer",
                                    "expires_in": 3600,
                                    "user": {
                                        "id": "user_123",
                                        "email": "student@example.com",
                                        "roles": ["student"]
                                    }
                                }
                            }
                        }
                    },
                    "401": {
                        "description": "Invalid credentials",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/auth/register": {
            "post": {
                "tags": ["authentication"],
                "summary": "User registration endpoint",
                "description": "Creates a new user account in the system.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/RegisterRequest"},
                            "example": {
                                "email": "newstudent@example.com",
                                "password": "securepassword123",
                                "username": "newstudent",
                                "role": "student"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "User created successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/LoginResponse"}
                            }
                        }
                    },
                    "409": {
                        "description": "User already exists",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/me": {
            "get": {
                "tags": ["rbac"],
                "summary": "Get current user's profile information",
                "description": "Returns the profile information of the currently authenticated user.",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {
                        "description": "User profile information",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UserProfile"},
                                "example": {
                                    "user_id": "user_123",
                                    "email": "student@example.com",
                                    "username": "student",
                                    "roles": ["student"],
                                    "permissions": ["read_questions", "create_questions"],
                                    "is_active": True,
                                    "metadata": {"grade": "12", "target_university": "MIT"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "/admin/dashboard": {
            "get": {
                "tags": ["admin"],
                "summary": "Admin dashboard with system overview",
                "description": "Provides system statistics and administrative information.",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {
                        "description": "Admin dashboard data",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "message": {"type": "string"},
                                        "user": {"type": "object"},
                                        "system_stats": {"type": "object"}
                                    }
                                },
                                "example": {
                                    "message": "Welcome to admin dashboard",
                                    "user": {
                                        "id": "admin_123",
                                        "email": "admin@example.com",
                                        "roles": ["admin"]
                                    },
                                    "system_stats": {
                                        "total_users": 1250,
                                        "active_sessions": 89,
                                        "system_health": "healthy"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/external/status": {
            "get": {
                "tags": ["external-api"],
                "summary": "External API status endpoint",
                "description": "External API status endpoint (requires API key).",
                "security": [{"ApiKeyAuth": []}],
                "responses": {
                    "200": {
                        "description": "External API status",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "service": {"type": "string"}
                                    }
                                },
                                "example": {"status": "ok", "service": "nlp-ai-microservice"}
                            }
                        }
                    }
                }
            }
        }
    }
    
    return openapi_schema


def save_openapi_json(schema: Dict[str, Any], output_dir: Path) -> None:
    """Save OpenAPI JSON schema to file"""
    output_file = output_dir / "openapi.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    
    print(f"OpenAPI JSON schema saved to: {output_file}")


def generate_redoc_html(schema: Dict[str, Any], output_dir: Path) -> None:
    """Generate ReDoc HTML documentation"""
    print("Generating ReDoc HTML documentation...")
    
    # ReDoc HTML template
    redoc_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>NLP/AI Microservice API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <redoc spec-url='openapi.json'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
</body>
</html>
"""
    
    output_file = output_dir / "redoc.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(redoc_html)
    
    print(f"ReDoc HTML documentation saved to: {output_file}")


def generate_postman_collection(schema: Dict[str, Any], output_dir: Path) -> None:
    """Generate Postman collection"""
    print("Generating Postman collection...")
    
    collection = {
        "info": {
            "name": "NLP/AI Microservice API",
            "description": "Comprehensive API collection for NLP/AI Microservice with SAT/UTBK educational content",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "version": "1.0.0"
        },
        "auth": {
            "type": "bearer",
            "bearer": [
                {
                    "key": "token",
                    "value": "{{jwt_token}}",
                    "type": "string"
                }
            ]
        },
        "variable": [
            {
                "key": "base_url",
                "value": "http://localhost:8000",
                "type": "string"
            },
            {
                "key": "jwt_token",
                "value": "",
                "type": "string"
            },
            {
                "key": "api_key",
                "value": "",
                "type": "string"
            }
        ],
        "item": []
    }
    
    # Add requests based on OpenAPI schema
    if "paths" in schema:
        for path, methods in schema["paths"].items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    request = {
                        "name": details.get("summary", f"{method.upper()} {path}"),
                        "request": {
                            "method": method.upper(),
                            "header": [
                                {
                                    "key": "Content-Type",
                                    "value": "application/json",
                                    "type": "text"
                                }
                            ],
                            "url": {
                                "raw": "{{base_url}}" + path,
                                "host": ["{{base_url}}"],
                                "path": path.strip("/").split("/")
                            }
                        },
                        "response": []
                    }
                    
                    # Add authentication headers
                    if "auth" in path or "admin" in path or "rbac" in path:
                        request["request"]["header"].append({
                            "key": "Authorization",
                            "value": "Bearer {{jwt_token}}",
                            "type": "text"
                        })
                    elif "external" in path:
                        request["request"]["header"].append({
                            "key": "X-API-Key",
                            "value": "{{api_key}}",
                            "type": "text"
                        })
                    
                    # Add request body for POST/PUT requests
                    if method.upper() in ["POST", "PUT", "PATCH"] and "requestBody" in details:
                        if "content" in details["requestBody"] and "application/json" in details["requestBody"]["content"]:
                            example = details["requestBody"]["content"]["application/json"].get("example", {})
                            request["request"]["body"] = {
                                "mode": "raw",
                                "raw": json.dumps(example, indent=2),
                                "options": {
                                    "raw": {
                                        "language": "json"
                                    }
                                }
                            }
                    
                    collection["item"].append(request)
    
    # Save Postman collection
    output_file = output_dir / "postman_collection.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)
    
    print(f"Postman collection saved to: {output_file}")


def generate_api_examples(output_dir: Path) -> None:
    """Generate API examples and test data"""
    print("Generating API examples and test data...")
    
    examples = {
        "sat_questions": APIExamples.SAT_MATH_QUESTION,
        "utbk_questions": APIExamples.UTBK_PHYSICS_QUESTION,
        "student_profiles": APIExamples.STUDENT_PROFILE,
        "educational_materials": APIExamples.EDUCATIONAL_MATERIAL,
        "api_examples": {
            "llm_generate": {
                "text": "Explain how to solve this SAT math problem: If 2x + 3y = 12 and x - y = 1, what is the value of x?",
                "model": "gpt-3.5-turbo"
            },
            "embedding_generate": {
                "text": "SAT math problem about quadratic equations",
                "model": "all-MiniLM-L6-v2"
            },
            "hybrid_search": {
                "query": "SAT math problems about algebra",
                "top_k": 10,
                "alpha": 0.6,
                "filter": {"type": "question", "subject": "math"}
            },
            "ingest_documents": {
                "texts": [
                    "If 2x + 3y = 12 and x - y = 1, what is the value of x?",
                    "What is the area of a circle with radius 5?"
                ],
                "metadata_list": [
                    {"type": "question", "subject": "math", "test_type": "SAT"},
                    {"type": "question", "subject": "geometry", "test_type": "SAT"}
                ]
            },
            "agent_execute": {
                "query": "Calculate the derivative of x² + 3x - 2 and explain the steps",
                "tools": ["calculator", "math"]
            },
            "login": {
                "email": "student@example.com",
                "password": "securepassword123"
            },
            "register": {
                "email": "newstudent@example.com",
                "password": "securepassword123",
                "username": "newstudent",
                "role": "student"
            }
        }
    }
    
    # Save examples
    output_file = output_dir / "api_examples.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(examples, f, indent=2, ensure_ascii=False)
    
    print(f"API examples saved to: {output_file}")


def generate_readme(output_dir: Path) -> None:
    """Generate README for API documentation"""
    print("Generating API documentation README...")
    
    readme_content = """# NLP/AI Microservice API Documentation

This directory contains comprehensive API documentation for the NLP/AI Microservice, specifically designed for educational content handling with SAT/UTBK data.

## Files

- `openapi.json` - Complete OpenAPI 3.0 specification
- `redoc.html` - Interactive ReDoc documentation (open in browser)
- `postman_collection.json` - Postman collection for API testing
- `api_examples.json` - Example requests and test data

## Quick Start

### 1. View Interactive Documentation

Open `redoc.html` in your web browser to view the interactive API documentation.

### 2. Import Postman Collection

1. Open Postman
2. Click "Import" 
3. Select `postman_collection.json`
4. Set environment variables:
   - `base_url`: http://localhost:8000 (or your server URL)
   - `jwt_token`: Your JWT token (obtained from login)
   - `api_key`: Your API key (for external endpoints)

### 3. Test with Examples

Use the examples in `api_examples.json` to test the API endpoints.

## Authentication

The API supports two authentication methods:

### JWT Token Authentication
- Use `/auth/login` to obtain JWT tokens
- Include `Authorization: Bearer <token>` header
- Required for user-specific endpoints

### API Key Authentication
- Include `X-API-Key: <your-api-key>` header
- Required for external API endpoints

## Educational Content

The API is specifically designed for educational content:

### SAT Questions
- Math, Reading, and Writing questions
- Multiple choice format with explanations
- Difficulty levels: easy, medium, hard

### UTBK Questions
- Indonesian university entrance exam questions
- Mathematics, Physics, Chemistry, Biology
- Indonesian language support

### Student Profiles
- Track student progress and preferences
- Identify weak and strong subjects
- Set study goals

## Key Endpoints

### LLM Operations
- `POST /llm/generate` - Generate text explanations
- `POST /llm/chat` - Interactive chat completion

### Vector Search
- `POST /search/hybrid` - Hybrid BM25 + semantic search
- `POST /search/questions` - Search educational questions
- `POST /search/materials` - Search study materials

### Content Management
- `POST /ingest` - Add documents to search index
- `POST /embedding/generate` - Generate text embeddings

### AI Agents
- `POST /agent/execute` - Execute AI agents with tools
- `GET /tools/list` - List available tools

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /me` - Get user profile

## Rate Limiting

- Default: 100 requests per minute per user/API key
- Exempt endpoints: `/health`, `/metrics`, `/docs`, `/openapi.json`, `/redoc`

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Support

For questions and support:
- Email: support@nlp-ai-microservice.com
- GitHub: https://github.com/your-org/nlp-ai-microservice
"""
    
    output_file = output_dir / "README.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"API documentation README saved to: {output_file}")


def main():
    """Main function to generate all documentation"""
    print("Generating comprehensive OpenAPI documentation for NLP/AI Microservice...")
    
    # Create output directory
    output_dir = ROOT / "docs" / "api"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate OpenAPI schema
    schema = generate_openapi_json()
    
    # Save all documentation files
    save_openapi_json(schema, output_dir)
    generate_redoc_html(schema, output_dir)
    generate_postman_collection(schema, output_dir)
    generate_api_examples(output_dir)
    generate_readme(output_dir)
    
    print(f"\n✅ All documentation generated successfully in: {output_dir}")
    print("\nNext steps:")
    print(f"1. Open {output_dir}/redoc.html in your browser to view interactive docs")
    print(f"2. Import {output_dir}/postman_collection.json into Postman")
    print(f"3. Use examples from {output_dir}/api_examples.json for testing")


if __name__ == "__main__":
    main()




#!/usr/bin/env python3
"""
Generate OpenAPI Documentation for NLP/AI Microservice

This script generates comprehensive OpenAPI documentation including:
- OpenAPI JSON schema
- ReDoc HTML documentation
- Postman collection
- API examples and test data
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
from main import app


def generate_openapi_json() -> Dict[str, Any]:
    """Generate OpenAPI JSON schema"""
    print("Generating OpenAPI JSON schema...")
    
    # Get the OpenAPI schema from FastAPI app
    openapi_schema = app.openapi()
    
    # Enhance with additional examples and documentation
    openapi_schema["info"]["x-examples"] = {
        "sat_math_question": APIExamples.SAT_MATH_QUESTION,
        "utbk_physics_question": APIExamples.UTBK_PHYSICS_QUESTION,
        "student_profile": APIExamples.STUDENT_PROFILE,
        "educational_material": APIExamples.EDUCATIONAL_MATERIAL
    }
    
    # Add educational content examples to paths
    if "paths" in openapi_schema:
        for path, methods in openapi_schema["paths"].items():
            for method, details in methods.items():
                if "requestBody" in details and "content" in details["requestBody"]:
                    for content_type, content_details in details["requestBody"]["content"].items():
                        if "schema" in content_details:
                            # Add examples based on endpoint
                            if "llm" in path:
                                content_details["example"] = {
                                    "text": "Explain how to solve this SAT math problem: If 2x + 3y = 12 and x - y = 1, what is the value of x?",
                                    "model": "gpt-3.5-turbo"
                                }
                            elif "embedding" in path:
                                content_details["example"] = {
                                    "text": "SAT math problem about quadratic equations",
                                    "model": "all-MiniLM-L6-v2"
                                }
                            elif "search" in path:
                                content_details["example"] = {
                                    "query": "SAT math problems about algebra",
                                    "top_k": 10,
                                    "alpha": 0.6,
                                    "filter": {"type": "question", "subject": "math"}
                                }
                            elif "ingest" in path:
                                content_details["example"] = {
                                    "texts": [
                                        "If 2x + 3y = 12 and x - y = 1, what is the value of x?",
                                        "What is the area of a circle with radius 5?"
                                    ],
                                    "metadata_list": [
                                        {"type": "question", "subject": "math", "test_type": "SAT"},
                                        {"type": "question", "subject": "geometry", "test_type": "SAT"}
                                    ]
                                }
                            elif "agent" in path:
                                content_details["example"] = {
                                    "query": "Calculate the derivative of x² + 3x - 2 and explain the steps",
                                    "tools": ["calculator", "math"]
                                }
                            elif "auth" in path and "login" in path:
                                content_details["example"] = {
                                    "email": "student@example.com",
                                    "password": "securepassword123"
                                }
                            elif "auth" in path and "register" in path:
                                content_details["example"] = {
                                    "email": "newstudent@example.com",
                                    "password": "securepassword123",
                                    "username": "newstudent",
                                    "role": "student"
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
        "sat_questions": [
            {
                "id": "sat_math_001",
                "text": "If 2x + 3y = 12 and x - y = 1, what is the value of x?",
                "type": "math",
                "difficulty": "medium",
                "subject": "algebra",
                "answer_choices": ["A) 3", "B) 4", "C) 5", "D) 6"],
                "correct_answer": "A",
                "explanation": "Solve the system of equations: x = 3, y = 2"
            },
            {
                "id": "sat_math_002",
                "text": "What is the area of a circle with radius 5?",
                "type": "math",
                "difficulty": "easy",
                "subject": "geometry",
                "answer_choices": ["A) 10π", "B) 25π", "C) 50π", "D) 100π"],
                "correct_answer": "B",
                "explanation": "Area = πr² = π(5)² = 25π"
            }
        ],
        "utbk_questions": [
            {
                "id": "utbk_math_001",
                "text": "Jika f(x) = x² + 2x - 3, maka nilai f(-1) adalah...",
                "type": "math",
                "difficulty": "easy",
                "subject": "matematika",
                "language": "indonesian",
                "answer_choices": ["A) -4", "B) -2", "C) 0", "D) 2"],
                "correct_answer": "A",
                "explanation": "f(-1) = (-1)² + 2(-1) - 3 = 1 - 2 - 3 = -4"
            },
            {
                "id": "utbk_physics_001",
                "text": "Sebuah benda bermassa 2 kg bergerak dengan kecepatan 5 m/s. Berapakah momentum benda tersebut?",
                "type": "physics",
                "difficulty": "easy",
                "subject": "fisika",
                "language": "indonesian",
                "answer_choices": ["A) 2 kg⋅m/s", "B) 5 kg⋅m/s", "C) 10 kg⋅m/s", "D) 25 kg⋅m/s"],
                "correct_answer": "C",
                "explanation": "p = mv = 2 kg × 5 m/s = 10 kg⋅m/s"
            }
        ],
        "student_profiles": [
            {
                "id": "student_001",
                "name": "Alice Johnson",
                "email": "alice.johnson@example.com",
                "grade": "12",
                "target_university": "MIT",
                "test_type": "SAT",
                "weak_subjects": ["math"],
                "strong_subjects": ["reading", "writing"],
                "study_goals": ["improve algebra", "practice geometry"]
            },
            {
                "id": "student_002",
                "name": "Budi Santoso",
                "email": "budi.santoso@example.com",
                "grade": "12",
                "target_university": "UI",
                "test_type": "UTBK",
                "weak_subjects": ["fisika"],
                "strong_subjects": ["matematika", "kimia"],
                "study_goals": ["master physics concepts", "improve problem solving"]
            }
        ],
        "educational_materials": [
            {
                "id": "material_001",
                "title": "SAT Math Formula Sheet",
                "content": "Important formulas for SAT Mathematics: Area of circle = πr², Quadratic formula = (-b ± √(b²-4ac))/2a, Distance formula = √((x₂-x₁)² + (y₂-y₁)²)",
                "type": "reference",
                "subject": "math",
                "difficulty": "all"
            },
            {
                "id": "material_002",
                "title": "UTBK Physics Concepts",
                "content": "Key physics concepts for UTBK: Newton's laws, momentum conservation, energy conservation, wave properties, electric fields",
                "type": "study_guide",
                "subject": "physics",
                "difficulty": "medium"
            }
        ],
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




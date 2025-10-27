"""
OpenAPI Schema Configuration for NLP/AI Microservice

This module provides comprehensive OpenAPI schema definitions and examples
for the NLP/AI microservice, specifically designed for educational content
handling with SAT/UTBK data.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class TestType(str, Enum):
    """Test type enumeration"""
    SAT = "SAT"
    UTBK = "UTBK"


class DifficultyLevel(str, Enum):
    """Difficulty level enumeration"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class SubjectType(str, Enum):
    """Subject type enumeration"""
    MATH = "math"
    READING = "reading"
    WRITING = "writing"
    SCIENCE = "science"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    MATEMATIKA = "matematika"
    FISIKA = "fisika"
    KIMIA = "kimia"


class LanguageType(str, Enum):
    """Language type enumeration"""
    ENGLISH = "english"
    INDONESIAN = "indonesian"


class UserRole(str, Enum):
    """User role enumeration"""
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class LLMProvider(str, Enum):
    """LLM provider enumeration"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LLAMA = "llama"


class EmbeddingModel(str, Enum):
    """Embedding model enumeration"""
    MINI_LM = "all-MiniLM-L6-v2"
    MPNET = "all-mpnet-base-v2"
    OPENAI_ADA = "text-embedding-ada-002"


# Request/Response Models

class TextRequest(BaseModel):
    """Text generation request model"""
    text: str = Field(..., description="The input text or prompt for generation", example="Explain how to solve quadratic equations for SAT preparation")
    model: Optional[str] = Field("gpt-3.5-turbo", description="The LLM model to use", example="gpt-3.5-turbo")


class TextResponse(BaseModel):
    """Text generation response model"""
    response: str = Field(..., description="The generated text response", example="Quadratic equations are polynomial equations of degree 2...")


class EmbeddingRequest(BaseModel):
    """Embedding generation request model"""
    text: str = Field(..., description="The text to convert to embeddings", example="SAT math problem about quadratic equations")
    model: Optional[str] = Field("all-MiniLM-L6-v2", description="The embedding model to use", example="all-MiniLM-L6-v2")


class EmbeddingResponse(BaseModel):
    """Embedding generation response model"""
    embedding: List[float] = Field(..., description="The embedding vector as a list of floating-point numbers", example=[0.1, 0.2, 0.3, 0.4, 0.5])


class BatchEmbeddingRequest(BaseModel):
    """Batch embedding generation request model"""
    text: str = Field(..., description="The text to convert to embeddings", example="SAT math problem about quadratic equations")
    model: Optional[str] = Field("all-MiniLM-L6-v2", description="The embedding model to use", example="all-MiniLM-L6-v2")


class BatchEmbeddingResponse(BaseModel):
    """Batch embedding generation response model"""
    embeddings: List[List[float]] = Field(..., description="List of embedding vectors", example=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])


class VectorSearchRequest(BaseModel):
    """Vector search request model"""
    query: str = Field(..., description="The search query", example="quadratic equations")
    top_k: Optional[int] = Field(5, description="Number of results to return", example=5)


class VectorSearchResponse(BaseModel):
    """Vector search response model"""
    results: List[Dict[str, Any]] = Field(..., description="List of search results with scores and metadata")


class HybridSearchRequest(BaseModel):
    """Hybrid search request model"""
    query: str = Field(..., description="The search query", example="SAT math problems about algebra")
    top_k: Optional[int] = Field(10, description="Number of results to return", example=10)
    alpha: Optional[float] = Field(0.6, description="Weight for BM25 vs semantic search (0.0-1.0)", example=0.6)
    filter: Optional[Dict[str, Any]] = Field(None, description="Optional metadata filters", example={"type": "question", "subject": "math"})


class HybridSearchResponse(BaseModel):
    """Hybrid search response model"""
    results: List[Dict[str, Any]] = Field(..., description="List of hybrid search results with combined scores")


class IngestRequest(BaseModel):
    """Document ingestion request model"""
    texts: List[str] = Field(..., description="List of text documents to ingest", example=["SAT math problem 1", "SAT math problem 2"])
    metadata_list: Optional[List[Dict[str, Any]]] = Field(None, description="Optional metadata for each document", example=[{"type": "question", "subject": "math"}, {"type": "question", "subject": "algebra"}])


class IngestResponse(BaseModel):
    """Document ingestion response model"""
    elastic_ids: List[str] = Field(..., description="Document IDs from Elasticsearch", example=["doc_1", "doc_2"])
    qdrant_ids: List[str] = Field(..., description="Document IDs from Qdrant", example=["qdrant_1", "qdrant_2"])


class AgentRequest(BaseModel):
    """Agent execution request model"""
    query: str = Field(..., description="The problem or question for the agent to solve", example="Calculate the derivative of x² + 3x - 2 and explain the steps")
    tools: Optional[List[str]] = Field([], description="List of tools the agent can use", example=["calculator", "math"])


class AgentResponse(BaseModel):
    """Agent execution response model"""
    result: str = Field(..., description="The agent's solution and reasoning process", example="I'll help you solve this step by step using the calculator tool...")


class LoginRequest(BaseModel):
    """User login request model"""
    email: str = Field(..., description="User's email address", example="student@example.com")
    password: str = Field(..., description="User's password", example="securepassword123")


class LoginResponse(BaseModel):
    """User login response model"""
    access_token: str = Field(..., description="JWT access token", example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    refresh_token: str = Field(..., description="JWT refresh token", example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field("bearer", description="Token type", example="bearer")
    expires_in: int = Field(..., description="Token expiration time in seconds", example=3600)
    user: Dict[str, Any] = Field(..., description="User information", example={"id": "user_123", "email": "student@example.com", "roles": ["student"]})


class RegisterRequest(BaseModel):
    """User registration request model"""
    email: str = Field(..., description="User's email address", example="newstudent@example.com")
    password: str = Field(..., description="User's password", example="securepassword123")
    username: Optional[str] = Field(None, description="User's username", example="newstudent")
    role: Optional[str] = Field("student", description="User's role", example="student")


class UserProfile(BaseModel):
    """User profile model"""
    user_id: str = Field(..., description="User's unique identifier", example="user_123")
    email: str = Field(..., description="User's email address", example="student@example.com")
    username: str = Field(..., description="User's username", example="student")
    roles: List[str] = Field(..., description="User's roles", example=["student"])
    permissions: List[str] = Field(..., description="User's permissions", example=["read_questions", "create_questions"])
    is_active: bool = Field(..., description="Whether the user account is active", example=True)
    metadata: Dict[str, Any] = Field(..., description="Additional user metadata", example={"grade": "12", "target_university": "MIT"})


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service health status", example="healthy")
    service: str = Field(..., description="Service name", example="nlp-ai-microservice")


class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str = Field(..., description="Error message", example="Invalid request parameters")
    error_code: Optional[str] = Field(None, description="Error code", example="INVALID_REQUEST")
    timestamp: Optional[str] = Field(None, description="Error timestamp", example="2024-01-01T00:00:00Z")


# Educational Content Models

class SATQuestion(BaseModel):
    """SAT question model"""
    id: str = Field(..., description="Question unique identifier", example="sat_math_001")
    text: str = Field(..., description="Question text", example="If 2x + 3y = 12 and x - y = 1, what is the value of x?")
    type: str = Field(..., description="Question type", example="math")
    difficulty: DifficultyLevel = Field(..., description="Question difficulty level", example="medium")
    subject: SubjectType = Field(..., description="Question subject", example="algebra")
    answer_choices: List[str] = Field(..., description="Answer choices", example=["A) 3", "B) 4", "C) 5", "D) 6"])
    correct_answer: str = Field(..., description="Correct answer", example="A")
    explanation: Optional[str] = Field(None, description="Question explanation", example="Solve the system of equations: x = 3, y = 2")


class UTBKQuestion(BaseModel):
    """UTBK question model"""
    id: str = Field(..., description="Question unique identifier", example="utbk_math_001")
    text: str = Field(..., description="Question text in Indonesian", example="Jika f(x) = x² + 2x - 3, maka nilai f(-1) adalah...")
    type: str = Field(..., description="Question type", example="math")
    difficulty: DifficultyLevel = Field(..., description="Question difficulty level", example="easy")
    subject: SubjectType = Field(..., description="Question subject", example="matematika")
    language: LanguageType = Field(..., description="Question language", example="indonesian")
    answer_choices: List[str] = Field(..., description="Answer choices", example=["A) -4", "B) -2", "C) 0", "D) 2"])
    correct_answer: str = Field(..., description="Correct answer", example="A")
    explanation: Optional[str] = Field(None, description="Question explanation", example="f(-1) = (-1)² + 2(-1) - 3 = 1 - 2 - 3 = -4")


class StudentProfile(BaseModel):
    """Student profile model"""
    id: str = Field(..., description="Student unique identifier", example="student_001")
    name: str = Field(..., description="Student's name", example="Alice Johnson")
    email: str = Field(..., description="Student's email", example="alice.johnson@example.com")
    grade: str = Field(..., description="Student's grade level", example="12")
    target_university: str = Field(..., description="Target university", example="MIT")
    test_type: TestType = Field(..., description="Test type (SAT or UTBK)", example="SAT")
    weak_subjects: List[str] = Field(..., description="Subjects where student needs improvement", example=["math"])
    strong_subjects: List[str] = Field(..., description="Student's strong subjects", example=["reading", "writing"])
    study_goals: List[str] = Field(..., description="Student's study goals", example=["improve algebra", "practice geometry"])


class EducationalMaterial(BaseModel):
    """Educational material model"""
    id: str = Field(..., description="Material unique identifier", example="material_001")
    title: str = Field(..., description="Material title", example="SAT Math Formula Sheet")
    content: str = Field(..., description="Material content", example="Important formulas for SAT Mathematics: Area of circle = πr²...")
    type: str = Field(..., description="Material type", example="reference")
    subject: SubjectType = Field(..., description="Material subject", example="math")
    difficulty: DifficultyLevel = Field(..., description="Material difficulty level", example="all")


# API Examples

class APIExamples:
    """API examples for documentation"""
    
    SAT_MATH_QUESTION = {
        "id": "sat_math_001",
        "text": "If 2x + 3y = 12 and x - y = 1, what is the value of x?",
        "type": "math",
        "difficulty": "medium",
        "subject": "algebra",
        "answer_choices": ["A) 3", "B) 4", "C) 5", "D) 6"],
        "correct_answer": "A",
        "explanation": "Solve the system of equations: x = 3, y = 2"
    }
    
    UTBK_PHYSICS_QUESTION = {
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
    
    STUDENT_PROFILE = {
        "id": "student_001",
        "name": "Alice Johnson",
        "email": "alice.johnson@example.com",
        "grade": "12",
        "target_university": "MIT",
        "test_type": "SAT",
        "weak_subjects": ["math"],
        "strong_subjects": ["reading", "writing"],
        "study_goals": ["improve algebra", "practice geometry"]
    }
    
    EDUCATIONAL_MATERIAL = {
        "id": "material_001",
        "title": "SAT Math Formula Sheet",
        "content": "Important formulas for SAT Mathematics: Area of circle = πr², Quadratic formula = (-b ± √(b²-4ac))/2a, Distance formula = √((x₂-x₁)² + (y₂-y₁)²)",
        "type": "reference",
        "subject": "math",
        "difficulty": "all"
    }


# OpenAPI Schema Configuration

def get_openapi_schema() -> Dict[str, Any]:
    """Get comprehensive OpenAPI schema configuration"""
    return {
        "openapi": "3.0.2",
        "info": {
            "title": "NLP/AI Microservice",
            "description": """
            ## NLP/AI Microservice for Educational Content

            A comprehensive FastAPI microservice providing Natural Language Processing and Artificial Intelligence capabilities for educational applications, specifically designed for SAT and UTBK (Indonesian university entrance exam) preparation.

            ### Key Features

            * **LLM Integration**: Support for OpenAI GPT, Anthropic Claude, and local LLaMA models
            * **Text Embeddings**: Generate embeddings using Sentence Transformers and OpenAI Ada
            * **Vector Search**: Hybrid search combining BM25 (Elasticsearch) and semantic search (Qdrant)
            * **Agent Execution**: AI agents with tool integration for complex problem solving
            * **Educational Content**: Specialized support for SAT/UTBK questions and materials
            * **RBAC Security**: Role-based access control with JWT and API key authentication
            * **Multi-language**: Support for English (SAT) and Indonesian (UTBK) content

            ### Educational Use Cases

            * SAT Math, Reading, and Writing preparation
            * UTBK Mathematics, Physics, Chemistry, and Biology questions
            * Personalized study recommendations
            * Automated question explanation generation
            * Student progress tracking and analytics

            ### Authentication

            The API supports two authentication methods:
            1. **JWT Tokens**: For user-based access with role-based permissions
            2. **API Keys**: For external integrations and service-to-service communication

            ### Rate Limiting

            API requests are rate-limited to ensure fair usage:
            - Default: 100 requests per minute per user/API key
            - Exempt endpoints: `/health`, `/metrics`, `/docs`, `/openapi.json`, `/redoc`
            """,
            "version": "1.0.0",
            "contact": {
                "name": "NLP/AI Microservice Support",
                "email": "support@nlp-ai-microservice.com",
                "url": "https://github.com/your-org/nlp-ai-microservice"
            },
            "license": {
                "name": "MIT License",
                "url": "https://opensource.org/licenses/MIT"
            }
        },
        "servers": [
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://api.nlp-ai-microservice.com",
                "description": "Production server"
            }
        ],
        "tags": [
            {
                "name": "health",
                "description": "Health check and system status endpoints"
            },
            {
                "name": "llm",
                "description": "Large Language Model operations for text generation and chat completion"
            },
            {
                "name": "embeddings",
                "description": "Text embedding generation for vector operations"
            },
            {
                "name": "vector-search",
                "description": "Vector database operations and similarity search"
            },
            {
                "name": "hybrid-search",
                "description": "Hybrid search combining BM25 and semantic search"
            },
            {
                "name": "agents",
                "description": "AI agent execution with tool integration"
            },
            {
                "name": "tools",
                "description": "Utility tools for AI agents (calculator, text analysis, etc.)"
            },
            {
                "name": "orchestration",
                "description": "Service orchestration and coordination endpoints"
            },
            {
                "name": "external-services",
                "description": "Integration with external services (User Service, Question Service, API Gateway)"
            },
            {
                "name": "authentication",
                "description": "User authentication, registration, and token management"
            },
            {
                "name": "rbac",
                "description": "Role-based access control endpoints for different user roles"
            },
            {
                "name": "admin",
                "description": "Administrative functions and system management"
            },
            {
                "name": "analytics",
                "description": "Analytics and reporting endpoints"
            },
            {
                "name": "external-api",
                "description": "External API endpoints requiring API key authentication"
            }
        ],
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "JWT token authentication for user-based access"
                },
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "API key authentication for external integrations"
                }
            },
            "schemas": {
                "TextRequest": TextRequest.model_json_schema(),
                "TextResponse": TextResponse.model_json_schema(),
                "EmbeddingRequest": EmbeddingRequest.model_json_schema(),
                "EmbeddingResponse": EmbeddingResponse.model_json_schema(),
                "BatchEmbeddingRequest": BatchEmbeddingRequest.model_json_schema(),
                "BatchEmbeddingResponse": BatchEmbeddingResponse.model_json_schema(),
                "VectorSearchRequest": VectorSearchRequest.model_json_schema(),
                "VectorSearchResponse": VectorSearchResponse.model_json_schema(),
                "HybridSearchRequest": HybridSearchRequest.model_json_schema(),
                "HybridSearchResponse": HybridSearchResponse.model_json_schema(),
                "IngestRequest": IngestRequest.model_json_schema(),
                "IngestResponse": IngestResponse.model_json_schema(),
                "AgentRequest": AgentRequest.model_json_schema(),
                "AgentResponse": AgentResponse.model_json_schema(),
                "LoginRequest": LoginRequest.model_json_schema(),
                "LoginResponse": LoginResponse.model_json_schema(),
                "RegisterRequest": RegisterRequest.model_json_schema(),
                "UserProfile": UserProfile.model_json_schema(),
                "HealthResponse": HealthResponse.model_json_schema(),
                "ErrorResponse": ErrorResponse.model_json_schema(),
                "SATQuestion": SATQuestion.model_json_schema(),
                "UTBKQuestion": UTBKQuestion.model_json_schema(),
                "StudentProfile": StudentProfile.model_json_schema(),
                "EducationalMaterial": EducationalMaterial.model_json_schema()
            }
        },
        "security": [
            {"BearerAuth": []},
            {"ApiKeyAuth": []}
        ]
    }


if __name__ == "__main__":
    import json
    schema = get_openapi_schema()
    print(json.dumps(schema, indent=2))




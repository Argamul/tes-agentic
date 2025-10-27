from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import List, Optional
import os
from dotenv import load_dotenv
import logging

# Auth & RBAC
from auth.dependencies import (
    require_roles, get_current_user, get_current_user_optional,
    require_permissions, require_all_permissions, require_admin,
    require_teacher_or_admin, require_student_or_above,
    require_user_management, require_course_management, require_content_management,
    require_system_management, require_analytics_access
)
from auth.api_key_middleware import APIKeyMiddleware, get_api_key_user, require_api_key_roles, require_api_key_permissions
from auth.rbac_middleware import RBACMiddleware, rbac_protect, admin_only, teacher_or_admin, student_or_above
from auth.models import User, UserRole, Permission

# Import modules
from llm_engine.llm_service import LLMService
from embedding_model.embedding_service import EmbeddingService
from vector_db.vector_service import VectorService
from vector_db.elasticsearch_service import ElasticBM25Service
from vector_db.qdrant_service import QdrantVectorService
from vector_db.hybrid_retriever import HybridRetriever
from agent_executor.agent_service import AgentService
from tools.tool_registry import ToolRegistry
from clients.api_clients import UserServiceClient, QuestionServiceClient, APIGatewayClient
from clients.grpc_clients import UserServiceGRPCClient, QuestionServiceGRPCClient, APIGatewayGRPCClient
from orchestrator_service import orchestrator_service, OrchestrationRequest, OrchestrationResponse
from middleware.rate_limit import RateLimitMiddleware
from observability.otel_setup import configure_json_logging, init_tracing
from metrics.prometheus import setup_metrics

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="NLP/AI Microservice",
    description="""
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
    version="1.0.0",
    contact={
        "name": "NLP/AI Microservice Support",
        "email": "support@nlp-ai-microservice.com",
        "url": "https://github.com/your-org/nlp-ai-microservice"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.nlp-ai-microservice.com",
            "description": "Production server"
        }
    ],
    tags_metadata=[
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
    ]
)

# Observability: logging and tracing
SERVICE_NAME = os.getenv("SERVICE_NAME", "nlp-ai-microservice")
configure_json_logging(SERVICE_NAME)
init_tracing(SERVICE_NAME, app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics endpoint for Prometheus
setup_metrics(app)

# Add RBAC middleware for automatic route protection
app.add_middleware(RBACMiddleware)

# Add API key middleware for external routes
app.add_middleware(APIKeyMiddleware)

# Rate limiting middleware (after API key, before handlers)
app.add_middleware(RateLimitMiddleware)

# Initialize services
llm_service = LLMService()
embedding_service = EmbeddingService()
vector_service = VectorService()
bm25_service = ElasticBM25Service()
qdrant_service = QdrantVectorService()
agent_service = AgentService()
tool_registry = ToolRegistry()
user_client = UserServiceClient()
question_client = QuestionServiceClient()
api_gateway_client = APIGatewayClient()

# Initialize gRPC clients
user_grpc_client = UserServiceGRPCClient()
question_grpc_client = QuestionServiceGRPCClient()
api_gateway_grpc_client = APIGatewayGRPCClient()

# Set up service dependencies
vector_service.set_embedding_service(embedding_service)
qdrant_service.set_embedding_service(embedding_service)
agent_service.set_tool_registry(tool_registry)

# Pydantic models
class TextRequest(BaseModel):
    text: str
    model: Optional[str] = "gpt-3.5-turbo"

class EmbeddingRequest(BaseModel):
    text: str
    model: Optional[str] = "all-MiniLM-L6-v2"

class VectorSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class HybridSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10
    alpha: Optional[float] = 0.6
    filter: Optional[dict] = None

class IngestRequest(BaseModel):
    texts: List[str]
    metadata_list: Optional[List[dict]] = None

class AgentRequest(BaseModel):
    query: str
    tools: Optional[List[str]] = []

class IndexUserQuestionsRequest(BaseModel):
    limit: Optional[int] = 10
    include_user: Optional[bool] = True

class OrchestrateUserAnswerRequest(BaseModel):
    user_id: str
    question: str
    limit: Optional[int] = 5


# Lifecycle events to clean up network clients
@app.on_event("shutdown")
async def _shutdown_clients():
    try:
        await user_client.aclose()
    except Exception:
        pass
    try:
        await question_client.aclose()
    except Exception:
        pass
    try:
        await api_gateway_client.aclose()
    except Exception:
        pass
    try:
        await user_grpc_client.aclose()
    except Exception:
        pass
    try:
        await question_grpc_client.aclose()
    except Exception:
        pass
    try:
        await api_gateway_grpc_client.aclose()
    except Exception:
        pass
    try:
        await orchestrator_service.cleanup()
    except Exception:
        pass

# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint to verify service status.
    
    Returns the current health status of the NLP/AI microservice.
    """
    return {"status": "healthy", "service": "nlp-ai-microservice"}

# LLM endpoints
@app.post("/llm/generate", tags=["llm"])
async def generate_text(request: TextRequest):
    """
    Generate text using Large Language Models.
    
    Supports multiple LLM providers including OpenAI GPT, Anthropic Claude, and local LLaMA models.
    Useful for generating explanations, summaries, and educational content.
    
    - **text**: The input prompt or question
    - **model**: The LLM model to use (default: gpt-3.5-turbo)
    
    Returns the generated text response from the selected LLM.
    """
    try:
        response = await llm_service.generate_text(request.text, request.model)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Sample external service integrations
@app.get("/users/{user_id}")
async def get_user_via_user_service(user_id: str):
    try:
        data = await user_client.get_user(user_id)
        return {"user": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"User service error: {str(e)}")

@app.post("/users/{user_id}/index-questions")
async def index_user_questions(user_id: str, body: IndexUserQuestionsRequest):
    try:
        # Fetch latest questions for the user from Question Service
        q = await question_client.get_user_questions(user_id, limit=body.limit or 10)
        questions = q.get("questions") or q.get("data") or q
        if not isinstance(questions, list):
            questions = []

        # Ingest into both BM25 and Vector DB with metadata
        texts = []
        metas = []
        for item in questions:
            text = item.get("text") or item.get("title") or item.get("body") or ""
            if not text:
                continue
            texts.append(text)
            metas.append({
                "type": "question",
                "user_id": user_id,
                "source": "question_service",
                "question_id": item.get("id"),
            })

        ids_es = bm25_service.add_documents_batch(texts, metas)
        ids_qdrant = await qdrant_service.add_documents_batch(texts, metas)

        result = {"count": len(texts), "elastic_ids": ids_es, "qdrant_ids": ids_qdrant}

        # Optionally fetch user profile
        user_info = None
        if body.include_user:
            try:
                user_info = await user_client.get_user(user_id)
            except Exception:
                user_info = None

        return {"ingested": result, "user": user_info}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/gateway/proxy")
async def gateway_proxy(path: str, method: str = "GET"):
    try:
        data = await api_gateway_client.proxy(method=method, path=path)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gateway error: {str(e)}")

@app.post("/orchestrate/answer")
async def orchestrate_user_answer(body: OrchestrateUserAnswerRequest):
    try:
        # 1) Fetch user context
        user = None
        try:
            user = await user_client.get_user(body.user_id)
        except Exception:
            user = None

        # 2) Use hybrid retrieval over user's questions/materials
        retriever = HybridRetriever(bm25_service=bm25_service, vector_service=qdrant_service, alpha=0.6)
        filt = {"user_id": body.user_id}
        context_results = await retriever.search(body.question, top_k=body.limit or 5, filter_metadata=filt)

        # 3) Build prompt and call LLM
        context_snippets = "\n\n".join([r.get("document", "") for r in context_results])
        prompt = f"Answer the user's question using the provided context.\n\nUser: {user}\n\nContext:\n{context_snippets}\n\nQuestion: {body.question}\nAnswer:"
        answer = await llm_service.generate_text(prompt)

        return {
            "user": user,
            "retrieved": context_results,
            "answer": answer,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Enhanced Orchestrator Endpoints
# =============================================================================

@app.post("/orchestrate/query", response_model=OrchestrationResponse)
async def orchestrate_comprehensive_query(request: OrchestrationRequest):
    """Comprehensive orchestration endpoint that coordinates all services"""
    try:
        response = await orchestrator_service.orchestrate_user_query(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orchestrate/index-questions/{user_id}")
async def index_user_questions_orchestrated(
    user_id: str, 
    limit: int = 50, 
    use_grpc: bool = False
):
    """Index user's questions into vector database using orchestrator"""
    try:
        result = await orchestrator_service.index_user_questions(user_id, limit, use_grpc)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orchestrate/health")
async def orchestrator_health_check(use_grpc: bool = False):
    """Get health status of all orchestrated services"""
    try:
        health_status = await orchestrator_service.get_service_health(use_grpc)
        return health_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orchestrate/services/discover")
async def discover_orchestrated_services():
    """Discover all services using service discovery"""
    try:
        services = await orchestrator_service.discover_services()
        return services
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Enhanced Service Integration Endpoints
# =============================================================================

@app.get("/services/user/{user_id}/profile")
async def get_user_profile_comprehensive(user_id: str, use_grpc: bool = False):
    """Get comprehensive user profile using both API and gRPC"""
    try:
        if use_grpc:
            await user_grpc_client.connect()
            user_data = await user_grpc_client.get_user(user_id)
            user_profile = await user_grpc_client.get_user_profile(user_id)
        else:
            user_data = await user_client.get_user(user_id)
            user_profile = await user_client.get_user_profile(user_id)
        
        return {
            "user_data": user_data,
            "user_profile": user_profile,
            "retrieved_via": "grpc" if use_grpc else "rest_api"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/services/questions/user/{user_id}")
async def get_user_questions_comprehensive(
    user_id: str, 
    page: int = 1, 
    page_size: int = 10,
    use_grpc: bool = False
):
    """Get user questions using both API and gRPC"""
    try:
        if use_grpc:
            await question_grpc_client.connect()
            questions_data = await question_grpc_client.get_user_questions(
                user_id, page, page_size
            )
        else:
            questions_data = await question_client.get_user_questions(
                user_id, page, page_size
            )
        
        return {
            "questions": questions_data,
            "retrieved_via": "grpc" if use_grpc else "rest_api"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/services/gateway/proxy")
async def proxy_through_gateway(
    method: str = "GET",
    path: str = "/",
    target_service: str = "",
    use_grpc: bool = False,
    **kwargs
):
    """Proxy request through API Gateway using both protocols"""
    try:
        if use_grpc:
            await api_gateway_grpc_client.connect()
            result = await api_gateway_grpc_client.proxy_request(
                method=method,
                path=path,
                target_service=target_service,
                **kwargs
            )
        else:
            result = await api_gateway_client.proxy(method, path, **kwargs)
        
        return {
            "result": result,
            "proxied_via": "grpc" if use_grpc else "rest_api"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/services/gateway/validate")
async def validate_request_through_gateway(
    method: str = "GET",
    path: str = "/",
    user_id: str = "",
    user_roles: List[str] = [],
    user_permissions: List[str] = [],
    use_grpc: bool = False
):
    """Validate request authorization through API Gateway"""
    try:
        if use_grpc:
            await api_gateway_grpc_client.connect()
            result = await api_gateway_grpc_client.validate_request(
                method=method,
                path=path,
                user_id=user_id,
                user_roles=user_roles,
                user_permissions=user_permissions
            )
        else:
            result = await api_gateway_client.validate_request(
                method=method,
                path=path,
                user_id=user_id,
                user_roles=user_roles,
                user_permissions=user_permissions
            )
        
        return {
            "validation_result": result,
            "validated_via": "grpc" if use_grpc else "rest_api"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/services/gateway/health/{service_name}")
async def get_service_health_through_gateway(service_name: str, use_grpc: bool = False):
    """Get service health through API Gateway"""
    try:
        if use_grpc:
            await api_gateway_grpc_client.connect()
            result = await api_gateway_grpc_client.get_service_health(service_name)
        else:
            result = await api_gateway_client.get_service_health(service_name)
        
        return {
            "health_status": result,
            "checked_via": "grpc" if use_grpc else "rest_api"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/services/gateway/rate-limit/check")
async def check_rate_limit_through_gateway(
    user_id: str = "",
    api_key: str = "",
    endpoint: str = "",
    service_name: str = "",
    use_grpc: bool = False
):
    """Check rate limit through API Gateway"""
    try:
        if use_grpc:
            await api_gateway_grpc_client.connect()
            result = await api_gateway_grpc_client.rate_limit_check(
                user_id=user_id,
                api_key=api_key,
                endpoint=endpoint,
                service_name=service_name
            )
        else:
            result = await api_gateway_client.rate_limit_check(
                user_id=user_id,
                api_key=api_key,
                endpoint=endpoint,
                service_name=service_name
            )
        
        return {
            "rate_limit_status": result,
            "checked_via": "grpc" if use_grpc else "rest_api"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/llm/chat", tags=["llm"])
async def chat_completion(request: TextRequest):
    """
    Chat completion using Large Language Models.
    
    Provides conversational AI capabilities for interactive tutoring and Q&A sessions.
    Ideal for educational scenarios where students need step-by-step guidance.
    
    - **text**: The user's message or question
    - **model**: The LLM model to use (default: gpt-3.5-turbo)
    
    Returns a conversational response from the LLM.
    """
    try:
        response = await llm_service.chat_completion(request.text, request.model)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Embedding endpoints
@app.post("/embedding/generate", tags=["embeddings"])
async def generate_embedding(request: EmbeddingRequest):
    """
    Generate text embeddings for vector operations.
    
    Converts text into high-dimensional vectors for similarity search and semantic analysis.
    Supports multiple embedding models including Sentence Transformers and OpenAI Ada.
    
    - **text**: The text to convert to embeddings
    - **model**: The embedding model to use (default: all-MiniLM-L6-v2)
    
    Returns the embedding vector as a list of floating-point numbers.
    """
    try:
        embedding = await embedding_service.generate_embedding(request.text, request.model)
        return {"embedding": embedding.tolist()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embedding/batch", tags=["embeddings"])
async def generate_batch_embeddings(request: List[EmbeddingRequest]):
    """
    Generate embeddings for multiple texts in batch.
    
    Efficiently processes multiple texts at once for better performance.
    Useful for indexing large datasets of educational content.
    
    - **request**: List of EmbeddingRequest objects containing text and model
    
    Returns a list of embedding vectors for all input texts.
    """
    try:
        texts = [req.text for req in request]
        model = request[0].model if request else "all-MiniLM-L6-v2"
        embeddings = await embedding_service.generate_batch_embeddings(texts, model)
        return {"embeddings": [emb.tolist() for emb in embeddings]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Vector database endpoints
@app.post("/vector/search")
async def vector_search(request: VectorSearchRequest):
    try:
        results = await vector_service.search(request.query, request.top_k)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vector/add")
async def add_to_vector_db(request: TextRequest):
    try:
        result = await vector_service.add_document(request.text)
        return {"status": "success", "id": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vector/get/{doc_id}")
async def get_vector_document(doc_id: str):
    try:
        doc = await vector_service.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest", tags=["vector-search"])
async def ingest_documents(request: IngestRequest):
    """
    Ingest documents into the vector database for search.
    
    Adds documents to both BM25 (Elasticsearch) and semantic (Qdrant) search indexes.
    Essential for building the educational content database.
    
    - **texts**: List of text documents to ingest
    - **metadata_list**: Optional metadata for each document
    
    Returns the document IDs from both search indexes.
    """
    try:
        # Add to Elastic for BM25
        ids_es = bm25_service.add_documents_batch(request.texts, request.metadata_list)
        # Add to Qdrant for vectors
        ids_qdrant = await qdrant_service.add_documents_batch(request.texts, request.metadata_list)
        # Also keep in existing Chroma for backward-compat
        await vector_service.add_documents_batch(request.texts, request.metadata_list)
        return {"elastic_ids": ids_es, "qdrant_ids": ids_qdrant}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/hybrid", tags=["hybrid-search"])
async def search_hybrid(request: HybridSearchRequest):
    """
    Perform hybrid search combining BM25 and semantic search.
    
    Combines keyword-based search (BM25) with semantic similarity search for optimal results.
    Ideal for finding relevant educational content and questions.
    
    - **query**: The search query
    - **top_k**: Number of results to return (default: 10)
    - **alpha**: Weight for BM25 vs semantic search (0.0-1.0, default: 0.6)
    - **filter**: Optional metadata filters
    
    Returns ranked search results with combined scores.
    """
    try:
        retriever = HybridRetriever(bm25_service=bm25_service, vector_service=qdrant_service, alpha=request.alpha)
        results = await retriever.search(request.query, top_k=request.top_k, filter_metadata=request.filter)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/questions", tags=["hybrid-search"])
async def search_questions(request: HybridSearchRequest):
    """
    Search specifically for questions in the educational database.
    
    Filters search results to only include content marked as questions.
    Useful for finding similar SAT/UTBK questions for practice.
    
    - **query**: The search query
    - **top_k**: Number of results to return (default: 10)
    - **alpha**: Weight for BM25 vs semantic search (0.0-1.0, default: 0.6)
    - **filter**: Additional metadata filters (type=question is automatically added)
    
    Returns ranked question results.
    """
    try:
        retriever = HybridRetriever(bm25_service=bm25_service, vector_service=qdrant_service, alpha=request.alpha)
        filt = request.filter or {}
        filt.update({"type": "question"})
        results = await retriever.search(request.query, top_k=request.top_k, filter_metadata=filt)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/materials", tags=["hybrid-search"])
async def search_materials(request: HybridSearchRequest):
    """
    Search specifically for educational materials and study guides.
    
    Filters search results to only include content marked as materials.
    Useful for finding study guides, formula sheets, and reference materials.
    
    - **query**: The search query
    - **top_k**: Number of results to return (default: 10)
    - **alpha**: Weight for BM25 vs semantic search (0.0-1.0, default: 0.6)
    - **filter**: Additional metadata filters (type=material is automatically added)
    
    Returns ranked material results.
    """
    try:
        retriever = HybridRetriever(bm25_service=bm25_service, vector_service=qdrant_service, alpha=request.alpha)
        filt = request.filter or {}
        filt.update({"type": "material"})
        results = await retriever.search(request.query, top_k=request.top_k, filter_metadata=filt)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Agent endpoints
@app.post("/agent/execute", tags=["agents"])
async def execute_agent(request: AgentRequest, user=Depends(get_current_user)):
    """
    Execute AI agent with tool integration.
    
    Runs an AI agent that can use various tools to solve complex problems.
    Ideal for multi-step problem solving and educational tutoring scenarios.
    
    - **query**: The problem or question for the agent to solve
    - **tools**: List of tools the agent can use (optional)
    
    Returns the agent's solution and reasoning process.
    """
    try:
        result = await agent_service.execute(request.query, request.tools)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Tools endpoints
@app.get("/tools/list", tags=["tools"])
async def list_tools(user=Depends(require_roles("admin", "teacher"))):
    """
    List available tools for AI agents.
    
    Returns a list of all available tools that can be used by AI agents.
    Requires teacher or admin role for access.
    
    Returns a list of tool definitions with names and descriptions.
    """
    try:
        tools = tool_registry.list_tools()
        return {"tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/execute", tags=["tools"])
async def execute_tool(tool_name: str, parameters: dict, user=Depends(require_roles("admin"))):
    """
    Execute a specific tool directly.
    
    Runs a tool with the provided parameters and returns the result.
    Requires admin role for direct tool execution.
    
    - **tool_name**: Name of the tool to execute
    - **parameters**: Parameters to pass to the tool
    
    Returns the tool execution result.
    """
    try:
        result = await tool_registry.execute_tool(tool_name, parameters)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# RBAC PROTECTED ROUTES - Different Role Access Levels
# =============================================================================

# =============================================================================
# User Profile and Basic Routes
# =============================================================================

@app.get("/me", tags=["rbac"])
async def get_current_user_profile(user: User = Depends(get_current_user)):
    """
    Get current user's profile information.
    
    Returns the profile information of the currently authenticated user.
    Requires valid JWT token.
    
    Returns user ID, email, username, roles, permissions, and metadata.
    """
    return {
        "user_id": user.id,
        "email": user.email,
        "username": user.username,
        "roles": [role.value for role in user.roles],
        "permissions": [perm.value for perm in user.get_all_permissions()],
        "is_active": user.is_active,
        "metadata": user.metadata
    }


@app.get("/auth/refresh")
async def refresh_token(refresh_token: str):
    """Refresh JWT token using refresh token."""
    from auth.auth_service import auth_service_singleton
    try:
        new_tokens = await auth_service_singleton.refresh_token(refresh_token)
        return {"tokens": new_tokens}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/auth/login", tags=["authentication"])
async def login(credentials: dict):
    """
    User login endpoint.
    
    Authenticates users and returns JWT tokens for API access.
    Delegates to external authentication service.
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns JWT access and refresh tokens along with user information.
    """
    from auth.auth_service import auth_service_singleton
    
    email = credentials.get("email")
    password = credentials.get("password")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    
    if not auth_service_singleton._configured:
        # Development mode - return mock tokens
        if os.getenv("ENVIRONMENT", "").lower() == "development":
            return {
                "access_token": "mock-access-token-12345",
                "refresh_token": "mock-refresh-token-67890",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": "dev-user-123",
                    "email": email,
                    "username": "devuser",
                    "roles": ["admin"],
                    "permissions": ["external_api_access"],
                    "is_active": True
                }
            }
        
        raise HTTPException(status_code=500, detail="Auth service not configured")
    
    # Call external auth service
    try:
        url = f"{auth_service_singleton.base_url.rstrip('/')}/login"
        payload = {"email": email, "password": password}
        
        async with httpx.AsyncClient(timeout=auth_service_singleton.timeout_seconds) as client:
            resp = await client.post(url, json=payload)
            
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        else:
            raise HTTPException(status_code=502, detail=f"Auth service error: {resp.status_code}")
            
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Auth service unreachable: {exc}")


@app.post("/auth/register", tags=["authentication"])
async def register(user_data: dict):
    """
    User registration endpoint.
    
    Creates a new user account in the system.
    Delegates to external authentication service.
    
    - **email**: User's email address
    - **password**: User's password
    - **username**: User's username (optional)
    - **role**: User's role (default: student)
    
    Returns user information and authentication tokens.
    """
    from auth.auth_service import auth_service_singleton
    
    email = user_data.get("email")
    password = user_data.get("password")
    username = user_data.get("username")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    
    if not auth_service_singleton._configured:
        raise HTTPException(status_code=500, detail="Auth service not configured")
    
    # Call external auth service
    try:
        url = f"{auth_service_singleton.base_url.rstrip('/')}/register"
        payload = {
            "email": email,
            "password": password,
            "username": username,
            "role": user_data.get("role", "student")  # Default to student
        }
        
        async with httpx.AsyncClient(timeout=auth_service_singleton.timeout_seconds) as client:
            resp = await client.post(url, json=payload)
            
        if resp.status_code == 201:
            return resp.json()
        elif resp.status_code == 409:
            raise HTTPException(status_code=409, detail="User already exists")
        else:
            raise HTTPException(status_code=502, detail=f"Auth service error: {resp.status_code}")
            
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Auth service unreachable: {exc}")


@app.post("/auth/logout")
async def logout(
    authorization: str = Header(default=None),
    user: User = Depends(get_current_user)
):
    """Logout user and revoke token."""
    from auth.auth_service import auth_service_singleton
    
    # Extract token from authorization header
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    
    if token:
        # Revoke token with auth service
        success = await auth_service_singleton.revoke_token(token)
        if not success and auth_service_singleton._configured:
            # If revocation failed and we're using external service, still return success
            # as the token might be invalid anyway
            pass
    
    return {"message": "Logged out successfully", "user_id": user.id}


# =============================================================================
# Admin-Only Routes
# =============================================================================

@app.get("/admin/dashboard", tags=["admin"])
async def admin_dashboard(user: User = Depends(require_admin)):
    """
    Admin dashboard with system overview.
    
    Provides system statistics and administrative information.
    Requires admin role for access.
    
    Returns system stats including total users, active sessions, and health status.
    """
    return {
        "message": "Welcome to admin dashboard",
        "user": {
            "id": user.id,
            "email": user.email,
            "roles": [role.value for role in user.roles]
        },
        "system_stats": {
            "total_users": 1250,
            "active_sessions": 89,
            "system_health": "healthy"
        }
    }


@app.get("/admin/users")
async def list_all_users(user: User = Depends(require_user_management)):
    """List all users in the system (admin only)."""
    return {
        "users": [
            {"id": "1", "email": "user1@example.com", "role": "student"},
            {"id": "2", "email": "user2@example.com", "role": "teacher"},
            {"id": "3", "email": "user3@example.com", "role": "admin"}
        ],
        "total": 3
    }


@app.post("/admin/users")
async def create_user(
    user_data: dict,
    admin_user: User = Depends(require_all_permissions(Permission.CREATE_USER))
):
    """Create a new user (admin only)."""
    return {
        "message": "User created successfully",
        "user_id": "new-user-123",
        "created_by": admin_user.id
    }


@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_user: User = Depends(require_all_permissions(Permission.DELETE_USER))
):
    """Delete a user (admin only)."""
    return {
        "message": f"User {user_id} deleted successfully",
        "deleted_by": admin_user.id
    }


@app.get("/admin/api-keys")
async def list_api_keys(admin_user: User = Depends(require_admin)):
    """List all API keys (admin only)."""
    from auth.api_key_middleware import APIKeyMiddleware
    
    # Get API key middleware instance
    middleware = None
    for mw in app.user_middleware:
        if isinstance(mw.cls, APIKeyMiddleware):
            middleware = mw.cls(app)
            break
    
    if not middleware:
        raise HTTPException(status_code=500, detail="API key middleware not found")
    
    # Return sanitized API key information
    api_keys = []
    for key, info in middleware.api_keys.items():
        api_keys.append({
            "key_id": info.key_id,
            "name": info.name,
            "roles": info.roles,
            "permissions": info.permissions,
            "is_active": info.is_active,
            "expires_at": info.expires_at,
            "created_at": info.created_at,
            "last_used_at": info.last_used_at,
            "usage_count": info.usage_count,
            "metadata": info.metadata,
            "key_preview": f"{key[:8]}...{key[-4:]}"  # Show partial key for identification
        })
    
    return {
        "api_keys": api_keys,
        "total": len(api_keys),
        "requested_by": admin_user.id
    }


@app.post("/admin/api-keys")
async def create_api_key(
    key_data: dict,
    admin_user: User = Depends(require_admin)
):
    """Create a new API key (admin only)."""
    import secrets
    import time
    
    name = key_data.get("name", "New API Key")
    roles = key_data.get("roles", ["student"])
    permissions = key_data.get("permissions", ["external_api_access"])
    expires_days = key_data.get("expires_days", 365)  # Default 1 year
    metadata = key_data.get("metadata", {})
    
    # Generate secure API key
    api_key = f"ak_{secrets.token_urlsafe(32)}"
    
    # Calculate expiration
    expires_at = int(time.time()) + (expires_days * 24 * 60 * 60)
    
    # Create API key info
    key_info = {
        "key": api_key,
        "key_id": f"key-{int(time.time())}",
        "name": name,
        "roles": roles,
        "permissions": permissions,
        "is_active": True,
        "expires_at": expires_at,
        "created_at": int(time.time()),
        "metadata": metadata
    }
    
    # In a real implementation, you would save this to a database
    # For now, we'll just return the key info
    return {
        "message": "API key created successfully",
        "api_key": api_key,  # Only returned once during creation
        "key_info": key_info,
        "created_by": admin_user.id,
        "warning": "Store this API key securely. It will not be shown again."
    }


@app.put("/admin/api-keys/{key_id}")
async def update_api_key(
    key_id: str,
    update_data: dict,
    admin_user: User = Depends(require_admin)
):
    """Update an API key (admin only)."""
    from auth.api_key_middleware import APIKeyMiddleware
    
    # Get API key middleware instance
    middleware = None
    for mw in app.user_middleware:
        if isinstance(mw.cls, APIKeyMiddleware):
            middleware = mw.cls(app)
            break
    
    if not middleware:
        raise HTTPException(status_code=500, detail="API key middleware not found")
    
    # Find the API key
    key_info = None
    target_key = None
    for key, info in middleware.api_keys.items():
        if info.key_id == key_id:
            key_info = info
            target_key = key
            break
    
    if not key_info:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Update allowed fields
    if "name" in update_data:
        key_info.name = update_data["name"]
    if "roles" in update_data:
        key_info.roles = update_data["roles"]
    if "permissions" in update_data:
        key_info.permissions = update_data["permissions"]
    if "is_active" in update_data:
        key_info.is_active = update_data["is_active"]
    if "metadata" in update_data:
        key_info.metadata.update(update_data["metadata"])
    
    return {
        "message": f"API key {key_id} updated successfully",
        "updated_by": admin_user.id,
        "key_info": {
            "key_id": key_info.key_id,
            "name": key_info.name,
            "roles": key_info.roles,
            "permissions": key_info.permissions,
            "is_active": key_info.is_active,
            "expires_at": key_info.expires_at,
            "created_at": key_info.created_at,
            "last_used_at": key_info.last_used_at,
            "usage_count": key_info.usage_count,
            "metadata": key_info.metadata
        }
    }


@app.delete("/admin/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    admin_user: User = Depends(require_admin)
):
    """Delete an API key (admin only)."""
    from auth.api_key_middleware import APIKeyMiddleware
    
    # Get API key middleware instance
    middleware = None
    for mw in app.user_middleware:
        if isinstance(mw.cls, APIKeyMiddleware):
            middleware = mw.cls(app)
            break
    
    if not middleware:
        raise HTTPException(status_code=500, detail="API key middleware not found")
    
    # Find and remove the API key
    target_key = None
    for key, info in middleware.api_keys.items():
        if info.key_id == key_id:
            target_key = key
            break
    
    if not target_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Remove from middleware (in production, this would be persisted to database)
    del middleware.api_keys[target_key]
    
    return {
        "message": f"API key {key_id} deleted successfully",
        "deleted_by": admin_user.id
    }


@app.get("/system/status")
async def system_status(user: User = Depends(require_system_management)):
    """Get system status and health metrics."""
    return {
        "status": "healthy",
        "uptime": "7 days, 3 hours",
        "memory_usage": "45%",
        "cpu_usage": "23%",
        "active_connections": 156
    }


# =============================================================================
# Teacher and Admin Routes
# =============================================================================

@app.get("/teacher/dashboard", tags=["rbac"])
async def teacher_dashboard(user: User = Depends(require_teacher_or_admin)):
    """
    Teacher dashboard with course management.
    
    Provides course management interface for teachers.
    Requires teacher or admin role for access.
    
    Returns course information and teaching statistics.
    """
    return {
        "message": "Welcome to teacher dashboard",
        "user": {
            "id": user.id,
            "email": user.email,
            "roles": [role.value for role in user.roles]
        },
        "courses": [
            {"id": "1", "name": "Mathematics 101", "students": 25},
            {"id": "2", "name": "Physics 201", "students": 18}
        ]
    }


@app.get("/courses")
async def list_courses(user: User = Depends(require_student_or_above)):
    """List all courses (students, teachers, admins)."""
    return {
        "courses": [
            {"id": "1", "name": "Mathematics 101", "instructor": "Dr. Smith"},
            {"id": "2", "name": "Physics 201", "instructor": "Dr. Johnson"},
            {"id": "3", "name": "Chemistry 101", "instructor": "Dr. Brown"}
        ]
    }


@app.post("/courses")
async def create_course(
    course_data: dict,
    user: User = Depends(require_course_management)
):
    """Create a new course (teachers and admins)."""
    return {
        "message": "Course created successfully",
        "course_id": "new-course-123",
        "created_by": user.id
    }


@app.put("/courses/{course_id}")
async def update_course(
    course_id: str,
    course_data: dict,
    user: User = Depends(require_course_management)
):
    """Update a course (teachers and admins)."""
    return {
        "message": f"Course {course_id} updated successfully",
        "updated_by": user.id
    }


@app.delete("/courses/{course_id}")
async def delete_course(
    course_id: str,
    user: User = Depends(require_all_permissions(Permission.DELETE_COURSE))
):
    """Delete a course (admins only)."""
    return {
        "message": f"Course {course_id} deleted successfully",
        "deleted_by": user.id
    }


@app.get("/content")
async def list_content(user: User = Depends(require_student_or_above)):
    """List all content (students, teachers, admins)."""
    return {
        "content": [
            {"id": "1", "title": "Introduction to Calculus", "type": "lesson"},
            {"id": "2", "title": "Physics Lab Manual", "type": "lab"},
            {"id": "3", "title": "Chemistry Quiz", "type": "quiz"}
        ]
    }


@app.post("/content")
async def create_content(
    content_data: dict,
    user: User = Depends(require_content_management)
):
    """Create new content (teachers and admins)."""
    return {
        "message": "Content created successfully",
        "content_id": "new-content-123",
        "created_by": user.id
    }


# =============================================================================
# Student Routes (Students, Teachers, Admins)
# =============================================================================

@app.get("/student/dashboard")
async def student_dashboard(user: User = Depends(require_student_or_above)):
    """Student dashboard with enrolled courses."""
    return {
        "message": "Welcome to student dashboard",
        "user": {
            "id": user.id,
            "email": user.email,
            "roles": [role.value for role in user.roles]
        },
        "enrolled_courses": [
            {"id": "1", "name": "Mathematics 101", "progress": "75%"},
            {"id": "2", "name": "Physics 201", "progress": "45%"}
        ]
    }


@app.get("/questions")
async def list_questions(user: User = Depends(require_student_or_above)):
    """List questions (students, teachers, admins)."""
    return {
        "questions": [
            {"id": "1", "text": "What is the derivative of x²?", "type": "math"},
            {"id": "2", "text": "Explain Newton's laws", "type": "physics"}
        ]
    }


@app.post("/questions")
async def create_question(
    question_data: dict,
    user: User = Depends(require_permissions(Permission.CREATE_QUESTION))
):
    """Create a new question (students, teachers, admins)."""
    return {
        "message": "Question created successfully",
        "question_id": "new-question-123",
        "created_by": user.id
    }


# =============================================================================
# Analytics and Reporting Routes
# =============================================================================

@app.get("/analytics/overview")
async def analytics_overview(user: User = Depends(require_analytics_access)):
    """Get analytics overview (teachers and admins)."""
    return {
        "total_students": 1250,
        "total_courses": 45,
        "completion_rate": "78%",
        "active_users": 89
    }


@app.get("/analytics/courses/{course_id}")
async def course_analytics(
    course_id: str,
    user: User = Depends(require_analytics_access)
):
    """Get analytics for a specific course."""
    return {
        "course_id": course_id,
        "enrollment": 25,
        "completion_rate": "85%",
        "average_score": "87.5"
    }


@app.get("/reports/student-progress")
async def student_progress_report(user: User = Depends(require_analytics_access)):
    """Generate student progress report."""
    return {
        "report_type": "student_progress",
        "generated_at": "2024-01-01T00:00:00Z",
        "data": [
            {"student_id": "1", "progress": "90%"},
            {"student_id": "2", "progress": "75%"}
        ]
    }


# =============================================================================
# External API Routes (API Key Authentication)
# =============================================================================

@app.get("/external/status")
async def external_status():
    """External API status endpoint (requires API key)."""
    return {"status": "ok", "service": "nlp-ai-microservice"}


@app.get("/external/health")
async def external_health():
    """External API health check (requires API key)."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0"
    }


@app.post("/external/llm/generate")
async def external_llm_generate(
    request: TextRequest,
    api_key_user = Depends(require_api_key_roles("admin", "teacher"))
):
    """External LLM generation endpoint (requires API key with admin/teacher role)."""
    try:
        response = await llm_service.generate_text(request.text, request.model)
        return {"response": response, "generated_by": "external_api"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/external/embedding/generate")
async def external_embedding_generate(
    request: EmbeddingRequest,
    api_key_user = Depends(require_api_key_permissions("external_api_access"))
):
    """External embedding generation endpoint (requires API key with external_api_access permission)."""
    try:
        embedding = await embedding_service.generate_embedding(request.text, request.model)
        return {"embedding": embedding.tolist(), "generated_by": "external_api"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Advanced RBAC Examples with Custom Logic
# =============================================================================

@app.get("/courses/{course_id}/students")
async def get_course_students(
    course_id: str,
    user: User = Depends(get_current_user)
):
    """Get students in a course with custom access control."""
    # Custom logic: Teachers can see students in their courses, admins can see all
    if UserRole.ADMIN in user.roles:
        # Admin can see all students
        students = [
            {"id": "1", "name": "John Doe", "email": "john@example.com"},
            {"id": "2", "name": "Jane Smith", "email": "jane@example.com"}
        ]
    elif UserRole.TEACHER in user.roles:
        # Teacher can only see students in their courses
        # In a real app, you'd check if the teacher teaches this course
        students = [
            {"id": "1", "name": "John Doe", "email": "john@example.com"},
            {"id": "2", "name": "Jane Smith", "email": "jane@example.com"}
        ]
    else:
        # Students can only see other students in the same course
        students = [
            {"id": "1", "name": "John Doe", "email": "john@example.com"}
        ]
    
    return {
        "course_id": course_id,
        "students": students,
        "requested_by": user.id
    }


@app.get("/my-permissions")
async def get_my_permissions(user: User = Depends(get_current_user)):
    """Get current user's permissions and roles."""
    return {
        "user_id": user.id,
        "roles": [role.value for role in user.roles],
        "permissions": [perm.value for perm in user.get_all_permissions()],
        "can_manage_users": user.has_permission(Permission.CREATE_USER),
        "can_manage_courses": user.has_permission(Permission.CREATE_COURSE),
        "can_view_analytics": user.has_permission(Permission.READ_ANALYTICS),
        "is_admin": user.has_role(UserRole.ADMIN),
        "is_teacher": user.has_role(UserRole.TEACHER),
        "is_student": user.has_role(UserRole.STUDENT)
    }


# =============================================================================
# Advanced RBAC Examples - Fine-grained Permission Control
# =============================================================================

@app.get("/assignments")
async def list_assignments(user: User = Depends(require_student_or_above)):
    """List assignments - students can see their own, teachers can see all in their courses."""
    assignments = [
        {
            "id": "1",
            "title": "Math Homework 1",
            "course_id": "math-101",
            "due_date": "2024-01-15",
            "status": "assigned"
        },
        {
            "id": "2", 
            "title": "Physics Lab Report",
            "course_id": "physics-201",
            "due_date": "2024-01-20",
            "status": "in_progress"
        }
    ]
    
    # Filter based on user role and permissions
    if user.has_role(UserRole.ADMIN):
        # Admins see all assignments
        filtered_assignments = assignments
    elif user.has_role(UserRole.TEACHER):
        # Teachers see assignments from their courses
        filtered_assignments = assignments  # In real app, filter by teacher's courses
    else:
        # Students see only their assignments
        filtered_assignments = assignments  # In real app, filter by student's enrollments
    
    return {
        "assignments": filtered_assignments,
        "total": len(filtered_assignments),
        "requested_by": user.id,
        "role": user.roles[0].value if user.roles else "unknown"
    }


@app.post("/assignments")
async def create_assignment(
    assignment_data: dict,
    user: User = Depends(require_course_management)
):
    """Create a new assignment - requires course management permission."""
    return {
        "message": "Assignment created successfully",
        "assignment_id": "new-assignment-123",
        "title": assignment_data.get("title", "Untitled Assignment"),
        "created_by": user.id,
        "required_permission": "course_management"
    }


@app.get("/assignments/{assignment_id}/submissions")
async def get_assignment_submissions(
    assignment_id: str,
    user: User = Depends(get_current_user)
):
    """Get submissions for an assignment with role-based filtering."""
    # Custom access control logic
    submissions = [
        {
            "id": "1",
            "assignment_id": assignment_id,
            "student_id": "student-1",
            "status": "submitted",
            "score": 95
        },
        {
            "id": "2",
            "assignment_id": assignment_id,
            "student_id": "student-2", 
            "status": "graded",
            "score": 87
        }
    ]
    
    # Role-based filtering
    if user.has_role(UserRole.ADMIN):
        # Admins see all submissions
        filtered_submissions = submissions
    elif user.has_role(UserRole.TEACHER):
        # Teachers see submissions for assignments they created
        filtered_submissions = submissions  # In real app, filter by teacher's assignments
    else:
        # Students see only their own submissions
        filtered_submissions = [s for s in submissions if s["student_id"] == user.id]
    
    return {
        "assignment_id": assignment_id,
        "submissions": filtered_submissions,
        "total": len(filtered_submissions),
        "requested_by": user.id,
        "access_level": "admin" if user.has_role(UserRole.ADMIN) else "limited"
    }


@app.post("/assignments/{assignment_id}/submit")
async def submit_assignment(
    assignment_id: str,
    submission_data: dict,
    user: User = Depends(require_student_or_above)
):
    """Submit an assignment - students and above can submit."""
    return {
        "message": "Assignment submitted successfully",
        "submission_id": "new-submission-123",
        "assignment_id": assignment_id,
        "submitted_by": user.id,
        "status": "submitted"
    }


@app.put("/assignments/{assignment_id}/grade")
async def grade_assignment(
    assignment_id: str,
    grade_data: dict,
    user: User = Depends(require_permissions(Permission.UPDATE_COURSE))
):
    """Grade an assignment - requires course update permission."""
    return {
        "message": "Assignment graded successfully",
        "assignment_id": assignment_id,
        "grade": grade_data.get("grade"),
        "graded_by": user.id,
        "required_permission": "update_course"
    }


# =============================================================================
# Resource Ownership Examples
# =============================================================================

@app.get("/my-courses")
async def get_my_courses(user: User = Depends(get_current_user)):
    """Get courses based on user's role and ownership."""
    all_courses = [
        {
            "id": "1",
            "name": "Mathematics 101",
            "instructor_id": "teacher-1",
            "students": ["student-1", "student-2"],
            "status": "active"
        },
        {
            "id": "2",
            "name": "Physics 201", 
            "instructor_id": "teacher-2",
            "students": ["student-1", "student-3"],
            "status": "active"
        }
    ]
    
    # Filter courses based on user's role and relationship
    if user.has_role(UserRole.ADMIN):
        # Admins see all courses
        my_courses = all_courses
        relationship = "admin"
    elif user.has_role(UserRole.TEACHER):
        # Teachers see courses they instruct
        my_courses = [c for c in all_courses if c["instructor_id"] == user.id]
        relationship = "instructor"
    else:
        # Students see courses they're enrolled in
        my_courses = [c for c in all_courses if user.id in c["students"]]
        relationship = "student"
    
    return {
        "courses": my_courses,
        "total": len(my_courses),
        "relationship": relationship,
        "user_id": user.id
    }


@app.get("/courses/{course_id}/details")
async def get_course_details(
    course_id: str,
    user: User = Depends(get_current_user)
):
    """Get detailed course information with access control."""
    course = {
        "id": course_id,
        "name": "Advanced Mathematics",
        "instructor_id": "teacher-1",
        "students": ["student-1", "student-2"],
        "assignments": ["assignment-1", "assignment-2"],
        "internal_notes": "This course covers advanced calculus topics",
        "public_description": "Learn advanced mathematical concepts"
    }
    
    # Determine what information the user can see
    if user.has_role(UserRole.ADMIN):
        # Admins see everything
        course_details = course
        access_level = "full"
    elif user.has_role(UserRole.TEACHER) and course["instructor_id"] == user.id:
        # Course instructor sees everything
        course_details = course
        access_level = "instructor"
    elif user.has_role(UserRole.STUDENT) and user.id in course["students"]:
        # Enrolled students see limited information
        course_details = {
            "id": course["id"],
            "name": course["name"],
            "public_description": course["public_description"],
            "assignments": course["assignments"]
        }
        access_level = "student"
    else:
        # No access
        raise HTTPException(
            status_code=403, 
            detail="Access denied: You don't have permission to view this course"
        )
    
    return {
        "course": course_details,
        "access_level": access_level,
        "requested_by": user.id
    }


# =============================================================================
# Permission-based Feature Flags
# =============================================================================

@app.get("/features")
async def get_available_features(user: User = Depends(get_current_user)):
    """Get available features based on user's permissions."""
    all_features = {
        "advanced_analytics": {
            "name": "Advanced Analytics",
            "description": "Access to detailed analytics and reports",
            "required_permission": Permission.READ_ANALYTICS.value
        },
        "user_management": {
            "name": "User Management", 
            "description": "Create, update, and delete users",
            "required_permission": Permission.CREATE_USER.value
        },
        "system_admin": {
            "name": "System Administration",
            "description": "System configuration and management",
            "required_permission": Permission.MANAGE_SYSTEM.value
        },
        "content_creation": {
            "name": "Content Creation",
            "description": "Create and edit course content",
            "required_permission": Permission.CREATE_CONTENT.value
        },
        "external_api": {
            "name": "External API Access",
            "description": "Access to external API endpoints",
            "required_permission": Permission.EXTERNAL_API_ACCESS.value
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
        "total_features": len(all_features),
        "available_count": len(available_features),
        "user_permissions": [perm.value for perm in user.get_all_permissions()]
    }

if __name__ == "__main__":
    cert_file = os.getenv("TLS_CERT_FILE")
    key_file = os.getenv("TLS_KEY_FILE")
    if cert_file and key_file:
        uvicorn.run(app, host="0.0.0.0", port=8000, ssl_certfile=cert_file, ssl_keyfile=key_file)
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)

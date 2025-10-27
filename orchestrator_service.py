"""
Orchestrator Service - Demonstrates how services interact with the orchestrator
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from clients.api_clients import UserServiceClient, QuestionServiceClient, APIGatewayClient
from clients.grpc_clients import UserServiceGRPCClient, QuestionServiceGRPCClient, APIGatewayGRPCClient
from clients.service_discovery import discover_service_async
from vector_db.hybrid_retriever import HybridRetriever
from vector_db.elasticsearch_service import ElasticBM25Service
from vector_db.qdrant_service import QdrantVectorService
from embedding_model.embedding_service import EmbeddingService
from llm_engine.llm_service import LLMService

logger = logging.getLogger(__name__)


class OrchestrationRequest(BaseModel):
    user_id: str
    query: str
    context_type: str = "questions"  # questions, materials, mixed
    max_results: int = 5
    include_user_context: bool = True
    use_grpc: bool = False


class OrchestrationResponse(BaseModel):
    user_context: Optional[Dict[str, Any]]
    retrieved_documents: List[Dict[str, Any]]
    generated_answer: str
    metadata: Dict[str, Any]
    processing_time_ms: float


class OrchestratorService:
    """
    Orchestrator service that coordinates between User Service, Question Service,
    API Gateway, and Vector DB to provide comprehensive answers
    """
    
    def __init__(self):
        # Initialize service clients
        self.user_api_client = UserServiceClient()
        self.question_api_client = QuestionServiceClient()
        self.api_gateway_client = APIGatewayClient()
        
        # Initialize gRPC clients
        self.user_grpc_client = UserServiceGRPCClient()
        self.question_grpc_client = QuestionServiceGRPCClient()
        self.api_gateway_grpc_client = APIGatewayGRPCClient()
        
        # Initialize vector services
        self.embedding_service = EmbeddingService()
        self.bm25_service = ElasticBM25Service()
        self.qdrant_service = QdrantVectorService()
        self.llm_service = LLMService()
        
        # Set up service dependencies
        self.qdrant_service.set_embedding_service(self.embedding_service)
        
        # Initialize hybrid retriever
        self.hybrid_retriever = HybridRetriever(
            bm25_service=self.bm25_service,
            vector_service=self.qdrant_service,
            alpha=0.6
        )
    
    async def orchestrate_user_query(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """
        Main orchestration method that coordinates all services to answer a user query
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Get user context
            user_context = None
            if request.include_user_context:
                user_context = await self._get_user_context(request.user_id, request.use_grpc)
            
            # Step 2: Retrieve relevant documents based on context type
            retrieved_docs = await self._retrieve_documents(
                request.query, 
                request.user_id, 
                request.context_type, 
                request.max_results
            )
            
            # Step 3: Generate comprehensive answer using LLM
            generated_answer = await self._generate_answer(
                request.query, 
                user_context, 
                retrieved_docs
            )
            
            # Step 4: Prepare metadata
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            metadata = {
                "query_type": request.context_type,
                "retrieval_method": "hybrid",
                "llm_model": "gpt-3.5-turbo",
                "document_count": len(retrieved_docs),
                "user_context_available": user_context is not None,
                "grpc_used": request.use_grpc
            }
            
            return OrchestrationResponse(
                user_context=user_context,
                retrieved_documents=retrieved_docs,
                generated_answer=generated_answer,
                metadata=metadata,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            raise
    
    async def _get_user_context(self, user_id: str, use_grpc: bool = False) -> Optional[Dict[str, Any]]:
        """Get user context from User Service"""
        try:
            if use_grpc:
                # Use gRPC client
                await self.user_grpc_client.connect()
                user_data = await self.user_grpc_client.get_user(user_id)
                user_profile = await self.user_grpc_client.get_user_profile(user_id)
            else:
                # Use REST API client
                user_data = await self.user_api_client.get_user(user_id)
                user_profile = await self.user_api_client.get_user_profile(user_id)
            
            return {
                "user_data": user_data,
                "user_profile": user_profile,
                "retrieved_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.warning(f"Failed to get user context for {user_id}: {e}")
            return None
    
    async def _retrieve_documents(self, query: str, user_id: str, context_type: str, max_results: int) -> List[Dict[str, Any]]:
        """Retrieve relevant documents using hybrid search"""
        try:
            # Set up filter based on context type
            filter_metadata = {"user_id": user_id}
            
            if context_type == "questions":
                filter_metadata["type"] = "question"
            elif context_type == "materials":
                filter_metadata["type"] = "material"
            # For "mixed", no type filter is applied
            
            # Perform hybrid search
            results = await self.hybrid_retriever.search(
                query=query,
                top_k=max_results,
                filter_metadata=filter_metadata
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Document retrieval failed: {e}")
            return []
    
    async def _generate_answer(self, query: str, user_context: Optional[Dict[str, Any]], 
                             retrieved_docs: List[Dict[str, Any]]) -> str:
        """Generate answer using LLM with context"""
        try:
            # Build context from retrieved documents
            context_snippets = []
            for doc in retrieved_docs:
                context_snippets.append(f"Document: {doc.get('document', '')}")
                if doc.get('metadata'):
                    context_snippets.append(f"Metadata: {doc['metadata']}")
            
            context_text = "\n\n".join(context_snippets)
            
            # Build user context
            user_info = ""
            if user_context and user_context.get("user_data"):
                user_data = user_context["user_data"]
                user_info = f"User: {user_data.get('username', 'Unknown')} ({user_data.get('email', '')})"
                if user_data.get('roles'):
                    user_info += f", Roles: {', '.join(user_data['roles'])}"
            
            # Construct prompt
            prompt = f"""Answer the user's question using the provided context.

{user_info}

Context:
{context_text}

Question: {query}

Please provide a comprehensive answer based on the context above. If the context doesn't contain enough information, please say so."""
            
            # Generate answer using LLM
            answer = await self.llm_service.generate_text(prompt, model="gpt-3.5-turbo")
            
            return answer
            
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return "I apologize, but I encountered an error while generating an answer. Please try again."
    
    async def index_user_questions(self, user_id: str, limit: int = 50, use_grpc: bool = False) -> Dict[str, Any]:
        """Index user's questions into vector database"""
        try:
            # Get user's questions
            if use_grpc:
                await self.question_grpc_client.connect()
                questions_data = await self.question_grpc_client.get_user_questions(user_id, page_size=limit)
                questions = questions_data.get("questions", [])
            else:
                questions_data = await self.question_api_client.get_user_questions(user_id, page_size=limit)
                questions = questions_data.get("questions", [])
            
            if not questions:
                return {"message": "No questions found for user", "indexed_count": 0}
            
            # Prepare documents for indexing
            texts = []
            metadata_list = []
            
            for question in questions:
                text = question.get("content") or question.get("title", "")
                if text:
                    texts.append(text)
                    metadata_list.append({
                        "type": "question",
                        "user_id": user_id,
                        "question_id": question.get("id"),
                        "category": question.get("category", ""),
                        "tags": ",".join(question.get("tags", [])),
                        "difficulty": question.get("difficulty", ""),
                        "created_at": question.get("created_at", ""),
                        "source": "question_service"
                    })
            
            # Index into both BM25 and vector databases
            bm25_ids = self.bm25_service.add_documents_batch(texts, metadata_list)
            vector_ids = await self.qdrant_service.add_documents_batch(texts, metadata_list)
            
            return {
                "message": "Questions indexed successfully",
                "indexed_count": len(texts),
                "bm25_ids": bm25_ids,
                "vector_ids": vector_ids
            }
            
        except Exception as e:
            logger.error(f"Question indexing failed: {e}")
            raise
    
    async def get_service_health(self, use_grpc: bool = False) -> Dict[str, Any]:
        """Get health status of all services"""
        health_status = {}
        
        try:
            if use_grpc:
                # Check gRPC services
                await self.user_grpc_client.connect()
                await self.question_grpc_client.connect()
                await self.api_gateway_grpc_client.connect()
                
                health_status["user_service_grpc"] = "connected"
                health_status["question_service_grpc"] = "connected"
                health_status["api_gateway_grpc"] = "connected"
            else:
                # Check REST API services
                user_health = await self.user_api_client._request("GET", "/health")
                question_health = await self.question_api_client._request("GET", "/health")
                gateway_health = await self.api_gateway_client._request("GET", "/health")
                
                health_status["user_service_api"] = "healthy" if user_health.status_code == 200 else "unhealthy"
                health_status["question_service_api"] = "healthy" if question_health.status_code == 200 else "unhealthy"
                health_status["api_gateway_api"] = "healthy" if gateway_health.status_code == 200 else "unhealthy"
            
            # Check vector services
            health_status["elasticsearch"] = "healthy"  # Simplified check
            health_status["qdrant"] = "healthy"  # Simplified check
            health_status["embedding_service"] = "healthy"  # Simplified check
            health_status["llm_service"] = "healthy"  # Simplified check
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_status["error"] = str(e)
        
        return health_status
    
    async def discover_services(self) -> Dict[str, Any]:
        """Discover all services using service discovery"""
        services = {}
        
        service_names = ["USER_SERVICE", "QUESTION_SERVICE", "API_GATEWAY"]
        
        for service_name in service_names:
            try:
                url = await discover_service_async(service_name)
                services[service_name] = {
                    "url": url,
                    "discovered": url is not None
                }
            except Exception as e:
                services[service_name] = {
                    "url": None,
                    "discovered": False,
                    "error": str(e)
                }
        
        return services
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.user_api_client.aclose()
            await self.question_api_client.aclose()
            await self.api_gateway_client.aclose()
            
            await self.user_grpc_client.aclose()
            await self.question_grpc_client.aclose()
            await self.api_gateway_grpc_client.aclose()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


# Global orchestrator instance
orchestrator_service = OrchestratorService()

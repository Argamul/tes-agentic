#!/usr/bin/env python3
"""
Service Integration Example

This script demonstrates how to use the API and gRPC client modules
to communicate with User Service, Question Service, and API Gateway.
It also shows how these services interact with the orchestrator.
"""

import asyncio
import json
import logging
from typing import Dict, Any

# Import our client modules
from clients.api_clients import UserServiceClient, QuestionServiceClient, APIGatewayClient
from clients.grpc_clients import UserServiceGRPCClient, QuestionServiceGRPCClient, APIGatewayGRPCClient
from clients.service_discovery import discover_service_async
from orchestrator_service import orchestrator_service, OrchestrationRequest

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_api_clients():
    """Demonstrate REST API client usage"""
    logger.info("=== Demonstrating REST API Clients ===")
    
    # Initialize API clients
    user_client = UserServiceClient()
    question_client = QuestionServiceClient()
    api_gateway_client = APIGatewayClient()
    
    try:
        # Example 1: Get user information
        logger.info("1. Getting user information...")
        try:
            user_data = await user_client.get_user("user-123")
            logger.info(f"User data: {json.dumps(user_data, indent=2)}")
        except Exception as e:
            logger.warning(f"Failed to get user: {e}")
        
        # Example 2: Get user questions
        logger.info("2. Getting user questions...")
        try:
            questions = await question_client.get_user_questions("user-123", limit=5)
            logger.info(f"User questions: {json.dumps(questions, indent=2)}")
        except Exception as e:
            logger.warning(f"Failed to get questions: {e}")
        
        # Example 3: Search questions
        logger.info("3. Searching questions...")
        try:
            search_results = await question_client.search_questions(
                query="machine learning",
                page=1,
                page_size=3
            )
            logger.info(f"Search results: {json.dumps(search_results, indent=2)}")
        except Exception as e:
            logger.warning(f"Failed to search questions: {e}")
        
        # Example 4: Proxy through API Gateway
        logger.info("4. Proxying through API Gateway...")
        try:
            proxy_result = await api_gateway_client.proxy("GET", "/health")
            logger.info(f"Gateway proxy result: {json.dumps(proxy_result, indent=2)}")
        except Exception as e:
            logger.warning(f"Failed to proxy through gateway: {e}")
        
        # Example 5: Validate request through gateway
        logger.info("5. Validating request through gateway...")
        try:
            validation = await api_gateway_client.validate_request(
                method="GET",
                path="/users/user-123",
                user_id="user-123",
                user_roles=["student"],
                user_permissions=["read_user"]
            )
            logger.info(f"Validation result: {json.dumps(validation, indent=2)}")
        except Exception as e:
            logger.warning(f"Failed to validate request: {e}")
    
    finally:
        # Clean up clients
        await user_client.aclose()
        await question_client.aclose()
        await api_gateway_client.aclose()


async def demonstrate_grpc_clients():
    """Demonstrate gRPC client usage"""
    logger.info("=== Demonstrating gRPC Clients ===")
    
    # Initialize gRPC clients
    user_grpc_client = UserServiceGRPCClient()
    question_grpc_client = QuestionServiceGRPCClient()
    api_gateway_grpc_client = APIGatewayGRPCClient()
    
    try:
        # Example 1: Get user information via gRPC
        logger.info("1. Getting user information via gRPC...")
        try:
            await user_grpc_client.connect()
            user_data = await user_grpc_client.get_user("user-123")
            logger.info(f"User data (gRPC): {json.dumps(user_data, indent=2)}")
        except Exception as e:
            logger.warning(f"Failed to get user via gRPC: {e}")
        
        # Example 2: Get user questions via gRPC
        logger.info("2. Getting user questions via gRPC...")
        try:
            await question_grpc_client.connect()
            questions = await question_grpc_client.get_user_questions("user-123", page_size=5)
            logger.info(f"User questions (gRPC): {json.dumps(questions, indent=2)}")
        except Exception as e:
            logger.warning(f"Failed to get questions via gRPC: {e}")
        
        # Example 3: Search questions via gRPC
        logger.info("3. Searching questions via gRPC...")
        try:
            search_results = await question_grpc_client.search_questions(
                query="artificial intelligence",
                page_size=3
            )
            logger.info(f"Search results (gRPC): {json.dumps(search_results, indent=2)}")
        except Exception as e:
            logger.warning(f"Failed to search questions via gRPC: {e}")
        
        # Example 4: Proxy through API Gateway via gRPC
        logger.info("4. Proxying through API Gateway via gRPC...")
        try:
            await api_gateway_grpc_client.connect()
            proxy_result = await api_gateway_grpc_client.proxy_request(
                method="GET",
                path="/health"
            )
            logger.info(f"Gateway proxy result (gRPC): {json.dumps(proxy_result, indent=2)}")
        except Exception as e:
            logger.warning(f"Failed to proxy through gateway via gRPC: {e}")
        
        # Example 5: Validate request through gateway via gRPC
        logger.info("5. Validating request through gateway via gRPC...")
        try:
            validation = await api_gateway_grpc_client.validate_request(
                method="GET",
                path="/users/user-123",
                user_id="user-123",
                user_roles=["teacher"],
                user_permissions=["read_user", "write_user"]
            )
            logger.info(f"Validation result (gRPC): {json.dumps(validation, indent=2)}")
        except Exception as e:
            logger.warning(f"Failed to validate request via gRPC: {e}")
    
    finally:
        # Clean up gRPC clients
        await user_grpc_client.aclose()
        await question_grpc_client.aclose()
        await api_gateway_grpc_client.aclose()


async def demonstrate_service_discovery():
    """Demonstrate service discovery functionality"""
    logger.info("=== Demonstrating Service Discovery ===")
    
    services = ["USER_SERVICE", "QUESTION_SERVICE", "API_GATEWAY"]
    
    for service_name in services:
        try:
            logger.info(f"Discovering {service_name}...")
            url = await discover_service_async(service_name)
            if url:
                logger.info(f"✓ {service_name} discovered at: {url}")
            else:
                logger.warning(f"✗ {service_name} not discovered")
        except Exception as e:
            logger.error(f"✗ Failed to discover {service_name}: {e}")


async def demonstrate_orchestrator():
    """Demonstrate orchestrator service functionality"""
    logger.info("=== Demonstrating Orchestrator Service ===")
    
    try:
        # Example 1: Comprehensive query orchestration
        logger.info("1. Orchestrating comprehensive query...")
        request = OrchestrationRequest(
            user_id="user-123",
            query="What are the best practices for machine learning model evaluation?",
            context_type="questions",
            max_results=5,
            include_user_context=True,
            use_grpc=False
        )
        
        response = await orchestrator_service.orchestrate_user_query(request)
        logger.info(f"Orchestration response: {json.dumps(response.dict(), indent=2)}")
        
        # Example 2: Index user questions
        logger.info("2. Indexing user questions...")
        index_result = await orchestrator_service.index_user_questions(
            user_id="user-123",
            limit=10,
            use_grpc=False
        )
        logger.info(f"Indexing result: {json.dumps(index_result, indent=2)}")
        
        # Example 3: Get service health
        logger.info("3. Getting service health...")
        health_status = await orchestrator_service.get_service_health(use_grpc=False)
        logger.info(f"Health status: {json.dumps(health_status, indent=2)}")
        
        # Example 4: Discover services
        logger.info("4. Discovering services...")
        services = await orchestrator_service.discover_services()
        logger.info(f"Discovered services: {json.dumps(services, indent=2)}")
    
    except Exception as e:
        logger.error(f"Orchestrator demonstration failed: {e}")
    
    finally:
        # Clean up orchestrator
        await orchestrator_service.cleanup()


async def demonstrate_vector_db_integration():
    """Demonstrate vector database integration with services"""
    logger.info("=== Demonstrating Vector DB Integration ===")
    
    try:
        # Example: Index questions and then search
        logger.info("1. Indexing sample questions...")
        
        # Sample questions to index
        sample_questions = [
            {
                "text": "What is machine learning and how does it work?",
                "metadata": {
                    "type": "question",
                    "user_id": "user-123",
                    "category": "AI/ML",
                    "difficulty": "beginner"
                }
            },
            {
                "text": "Explain the difference between supervised and unsupervised learning",
                "metadata": {
                    "type": "question",
                    "user_id": "user-123",
                    "category": "AI/ML",
                    "difficulty": "intermediate"
                }
            },
            {
                "text": "How do you evaluate the performance of a machine learning model?",
                "metadata": {
                    "type": "question",
                    "user_id": "user-123",
                    "category": "AI/ML",
                    "difficulty": "advanced"
                }
            }
        ]
        
        # Index questions using orchestrator
        for question in sample_questions:
            try:
                # This would typically be done through the orchestrator
                logger.info(f"Indexing question: {question['text'][:50]}...")
                # In a real scenario, this would call the orchestrator's indexing method
            except Exception as e:
                logger.warning(f"Failed to index question: {e}")
        
        logger.info("2. Vector DB integration demonstration completed")
    
    except Exception as e:
        logger.error(f"Vector DB integration demonstration failed: {e}")


async def main():
    """Main demonstration function"""
    logger.info("Starting Service Integration Demonstration")
    logger.info("=" * 60)
    
    try:
        # Run all demonstrations
        await demonstrate_service_discovery()
        await demonstrate_api_clients()
        await demonstrate_grpc_clients()
        await demonstrate_vector_db_integration()
        await demonstrate_orchestrator()
        
        logger.info("=" * 60)
        logger.info("Service Integration Demonstration Completed Successfully!")
    
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        raise


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())




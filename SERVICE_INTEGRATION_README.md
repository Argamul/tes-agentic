# Service Integration Guide

This guide demonstrates how to implement and use API and gRPC client modules to communicate with User Service, Question Service, and API Gateway, along with service discovery support using Consul or Istio.

## Overview

The service integration system provides:

1. **REST API Clients** - HTTP-based communication with external services
2. **gRPC Clients** - High-performance binary protocol communication
3. **Service Discovery** - Automatic service location using Consul, Istio, or etcd
4. **Orchestrator Service** - Coordinates between all services for comprehensive operations
5. **Vector DB Integration** - Stores and retrieves embeddings for semantic search

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Service  │    │ Question Service│    │  API Gateway    │
│                 │    │                 │    │                 │
│ REST API + gRPC │    │ REST API + gRPC │    │ REST API + gRPC │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Orchestrator   │
                    │     Service     │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Vector DB     │
                    │ (Elastic + Qdrant)│
                    └─────────────────┘
```

## Quick Start

### 1. Environment Setup

Create a `.env` file with the following configuration:

```bash
# Service URLs (optional - will use service discovery if not provided)
USER_SERVICE_URL=http://localhost:8001
QUESTION_SERVICE_URL=http://localhost:8002
API_GATEWAY_URL=http://localhost:8003

# gRPC Service Targets
USER_SERVICE_GRPC_TARGET=localhost:50051
QUESTION_SERVICE_GRPC_TARGET=localhost:50052
API_GATEWAY_GRPC_TARGET=localhost:50053

# Service Discovery Configuration
CONSUL_HOST=localhost
CONSUL_PORT=8500
CONSUL_TOKEN=your-consul-token

# Istio/Kubernetes Configuration
USE_ISTIO_DNS=true
ISTIO_NAMESPACE=default
K8S_CLUSTER_DOMAIN=cluster.local

# TLS Configuration
GRPC_TLS_ENABLED=false
GRPC_CERT_FILE=/path/to/cert.pem
GRPC_KEY_FILE=/path/to/key.pem
GRPC_CA_FILE=/path/to/ca.pem

# Service Discovery Cache
SERVICE_DISCOVERY_CACHE_TTL_SECONDS=30
```

### 2. Generate gRPC Stubs

```bash
# Install gRPC tools
pip install grpcio-tools

# Generate Python stubs from proto files
python scripts/generate_grpc_stubs.py
```

### 3. Run the Example

```bash
# Run the comprehensive example
python examples/service_integration_example.py
```

## API Client Usage

### REST API Clients

```python
from clients.api_clients import UserServiceClient, QuestionServiceClient, APIGatewayClient

# Initialize clients
user_client = UserServiceClient()
question_client = QuestionServiceClient()
api_gateway_client = APIGatewayClient()

# Get user information
user_data = await user_client.get_user("user-123")

# Get user questions
questions = await question_client.get_user_questions("user-123", limit=10)

# Search questions
search_results = await question_client.search_questions(
    query="machine learning",
    page=1,
    page_size=5
)

# Proxy through API Gateway
proxy_result = await api_gateway_client.proxy("GET", "/health")

# Validate request through gateway
validation = await api_gateway_client.validate_request(
    method="GET",
    path="/users/user-123",
    user_id="user-123",
    user_roles=["student"],
    user_permissions=["read_user"]
)

# Clean up
await user_client.aclose()
await question_client.aclose()
await api_gateway_client.aclose()
```

### gRPC Clients

```python
from clients.grpc_clients import UserServiceGRPCClient, QuestionServiceGRPCClient, APIGatewayGRPCClient

# Initialize gRPC clients
user_grpc_client = UserServiceGRPCClient()
question_grpc_client = QuestionServiceGRPCClient()
api_gateway_grpc_client = APIGatewayGRPCClient()

# Connect to services
await user_grpc_client.connect()
await question_grpc_client.connect()
await api_gateway_grpc_client.connect()

# Get user information via gRPC
user_data = await user_grpc_client.get_user("user-123")

# Get user questions via gRPC
questions = await question_grpc_client.get_user_questions("user-123", page_size=10)

# Search questions via gRPC
search_results = await question_grpc_client.search_questions(
    query="artificial intelligence",
    page_size=5
)

# Proxy through API Gateway via gRPC
proxy_result = await api_gateway_grpc_client.proxy_request(
    method="GET",
    path="/health"
)

# Validate request through gateway via gRPC
validation = await api_gateway_grpc_client.validate_request(
    method="GET",
    path="/users/user-123",
    user_id="user-123",
    user_roles=["teacher"],
    user_permissions=["read_user", "write_user"]
)

# Clean up
await user_grpc_client.aclose()
await question_grpc_client.aclose()
await api_gateway_grpc_client.aclose()
```

## Service Discovery

### Automatic Service Discovery

```python
from clients.service_discovery import discover_service_async

# Discover services automatically
user_service_url = await discover_service_async("USER_SERVICE")
question_service_url = await discover_service_async("QUESTION_SERVICE")
api_gateway_url = await discover_service_async("API_GATEWAY")

print(f"User Service: {user_service_url}")
print(f"Question Service: {question_service_url}")
print(f"API Gateway: {api_gateway_url}")
```

### Service Discovery Methods

The system supports multiple service discovery methods:

1. **Consul** - HashiCorp Consul for service registry
2. **Istio** - Kubernetes service mesh with DNS-based discovery
3. **etcd** - Distributed key-value store for service registry
4. **Environment Variables** - Direct URL configuration

### Consul Configuration

```bash
# Register services with Consul
curl -X PUT http://localhost:8500/v1/agent/service/register \
  -d '{
    "ID": "user-service-1",
    "Name": "USER_SERVICE",
    "Tags": ["api", "user"],
    "Address": "localhost",
    "Port": 8001,
    "Check": {
      "HTTP": "http://localhost:8001/health",
      "Interval": "10s"
    }
  }'
```

### Istio Configuration

```yaml
# Kubernetes service for Istio
apiVersion: v1
kind: Service
metadata:
  name: user-service
  namespace: default
spec:
  selector:
    app: user-service
  ports:
  - port: 80
    targetPort: 8001
---
# Istio VirtualService
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: user-service
spec:
  hosts:
  - user-service
  http:
  - route:
    - destination:
        host: user-service
```

## Orchestrator Service

The Orchestrator Service coordinates between all services to provide comprehensive functionality.

### Basic Orchestration

```python
from orchestrator_service import orchestrator_service, OrchestrationRequest

# Create orchestration request
request = OrchestrationRequest(
    user_id="user-123",
    query="What are the best practices for machine learning?",
    context_type="questions",  # questions, materials, mixed
    max_results=5,
    include_user_context=True,
    use_grpc=False
)

# Execute orchestration
response = await orchestrator_service.orchestrate_user_query(request)

print(f"Answer: {response.generated_answer}")
print(f"Retrieved documents: {len(response.retrieved_documents)}")
print(f"Processing time: {response.processing_time_ms}ms")
```

### Index User Questions

```python
# Index user's questions into vector database
result = await orchestrator_service.index_user_questions(
    user_id="user-123",
    limit=50,
    use_grpc=False
)

print(f"Indexed {result['indexed_count']} questions")
```

### Service Health Check

```python
# Get health status of all services
health_status = await orchestrator_service.get_service_health(use_grpc=False)

for service, status in health_status.items():
    print(f"{service}: {status}")
```

## API Endpoints

The system provides comprehensive REST API endpoints for all functionality:

### Orchestrator Endpoints

- `POST /orchestrate/query` - Comprehensive query orchestration
- `POST /orchestrate/index-questions/{user_id}` - Index user questions
- `GET /orchestrate/health` - Get service health status
- `GET /orchestrate/services/discover` - Discover all services

### Service Integration Endpoints

- `GET /services/user/{user_id}/profile` - Get comprehensive user profile
- `GET /services/questions/user/{user_id}` - Get user questions
- `POST /services/gateway/proxy` - Proxy through API Gateway
- `POST /services/gateway/validate` - Validate request authorization
- `GET /services/gateway/health/{service_name}` - Get service health
- `POST /services/gateway/rate-limit/check` - Check rate limits

### Example API Calls

```bash
# Comprehensive query orchestration
curl -X POST "http://localhost:8000/orchestrate/query" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "query": "What is machine learning?",
    "context_type": "questions",
    "max_results": 5,
    "include_user_context": true,
    "use_grpc": false
  }'

# Index user questions
curl -X POST "http://localhost:8000/orchestrate/index-questions/user-123?limit=50&use_grpc=false"

# Get service health
curl -X GET "http://localhost:8000/orchestrate/health?use_grpc=false"

# Discover services
curl -X GET "http://localhost:8000/orchestrate/services/discover"
```

## Vector Database Integration

The system integrates with multiple vector databases for semantic search:

### Elasticsearch (BM25)

```python
from vector_db.elasticsearch_service import ElasticBM25Service

bm25_service = ElasticBM25Service()

# Add documents
doc_ids = bm25_service.add_documents_batch(
    texts=["Document 1", "Document 2"],
    metadata_list=[{"type": "question"}, {"type": "material"}]
)
```

### Qdrant (Vector Search)

```python
from vector_db.qdrant_service import QdrantVectorService
from embedding_model.embedding_service import EmbeddingService

embedding_service = EmbeddingService()
qdrant_service = QdrantVectorService()
qdrant_service.set_embedding_service(embedding_service)

# Add documents with embeddings
vector_ids = await qdrant_service.add_documents_batch(
    texts=["Document 1", "Document 2"],
    metadata_list=[{"type": "question"}, {"type": "material"}]
)
```

### Hybrid Retrieval

```python
from vector_db.hybrid_retriever import HybridRetriever

# Combine BM25 and vector search
retriever = HybridRetriever(
    bm25_service=bm25_service,
    vector_service=qdrant_service,
    alpha=0.6  # Weight between BM25 and vector search
)

# Search with hybrid approach
results = await retriever.search(
    query="machine learning best practices",
    top_k=10,
    filter_metadata={"user_id": "user-123"}
)
```

## Error Handling

All clients include comprehensive error handling:

```python
try:
    user_data = await user_client.get_user("user-123")
except httpx.HTTPStatusError as e:
    print(f"HTTP error: {e.response.status_code}")
except httpx.RequestError as e:
    print(f"Request error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance Considerations

### Connection Pooling

- HTTP clients use connection pooling for better performance
- gRPC clients maintain persistent connections
- Service discovery results are cached to reduce lookup overhead

### Timeout Configuration

```bash
# Configure timeouts
USER_SERVICE_TIMEOUT_SECONDS=5
QUESTION_SERVICE_TIMEOUT_SECONDS=5
API_GATEWAY_TIMEOUT_SECONDS=5
CONSUL_HTTP_TIMEOUT_SECONDS=2
```

### Caching

```bash
# Service discovery cache TTL
SERVICE_DISCOVERY_CACHE_TTL_SECONDS=30
```

## Security

### TLS Configuration

```bash
# Enable TLS for gRPC
GRPC_TLS_ENABLED=true
GRPC_CERT_FILE=/path/to/client-cert.pem
GRPC_KEY_FILE=/path/to/client-key.pem
GRPC_CA_FILE=/path/to/ca-cert.pem

# TLS verification for HTTP
OUTBOUND_TLS_VERIFY=true
OUTBOUND_CA_BUNDLE=/path/to/ca-bundle.pem
OUTBOUND_CLIENT_CERT=/path/to/client-cert.pem
OUTBOUND_CLIENT_KEY=/path/to/client-key.pem
```

### Authentication

- API Gateway handles authentication and authorization
- JWT tokens for user authentication
- API keys for service-to-service communication
- Role-based access control (RBAC)

## Monitoring and Observability

### Health Checks

```python
# Check individual service health
health_status = await orchestrator_service.get_service_health()

# Check through API Gateway
gateway_health = await api_gateway_client.get_service_health("USER_SERVICE")
```

### Metrics

The system integrates with Prometheus for metrics collection:

- Request counts and response times
- Error rates
- Service discovery success rates
- Vector database operation metrics

### Logging

Structured logging with correlation IDs for request tracing:

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Processing user query", extra={
    "user_id": "user-123",
    "query": "machine learning",
    "correlation_id": "req-456"
})
```

## Troubleshooting

### Common Issues

1. **Service Discovery Failures**
   - Check Consul/Istio configuration
   - Verify network connectivity
   - Check service registration

2. **gRPC Connection Issues**
   - Verify gRPC stubs are generated
   - Check TLS configuration
   - Ensure service is running on correct port

3. **Vector Database Issues**
   - Check Elasticsearch/Qdrant connectivity
   - Verify embedding service configuration
   - Check document indexing

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
python examples/service_integration_example.py --verbose
```

## Contributing

1. Follow the existing code structure
2. Add comprehensive error handling
3. Include unit tests for new functionality
4. Update documentation for new features
5. Ensure backward compatibility

## License

This project is licensed under the MIT License - see the LICENSE file for details.




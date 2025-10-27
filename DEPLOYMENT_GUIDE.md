# NLP/AI Service Deployment Guide

This guide provides comprehensive instructions for deploying the NLP/AI microservice with Docker, Kubernetes, and Redis caching.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development with Docker Compose](#local-development-with-docker-compose)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Redis Caching Configuration](#redis-caching-configuration)
5. [Monitoring and Observability](#monitoring-and-observability)
6. [Auto-scaling Configuration](#auto-scaling-configuration)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software
- Docker 20.10+
- Docker Compose 2.0+
- Kubernetes 1.24+
- kubectl 1.24+
- Helm 3.0+ (optional)

### Required Environment Variables
Create a `.env` file with the following variables:

```bash
# API Keys
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Redis Configuration
REDIS_CACHE_ENABLED=true
REDIS_CACHE_TTL_SECONDS=600

# LLM Configuration
DEFAULT_LLM_PROVIDER=openai
LLM_PROVIDER_FALLBACK_ORDER=openai,anthropic,llama
TEMPERATURE=0.7
MAX_TOKENS=1000

# Monitoring
GRAFANA_PASSWORD=admin
LOG_LEVEL=INFO
ENVIRONMENT=production
```

## Local Development with Docker Compose

### 1. Start the Services

```bash
# Build and start all services
docker-compose up --build

# Start in detached mode
docker-compose up -d --build

# View logs
docker-compose logs -f api
```

### 2. Access the Services

- **API Service**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Redis**: localhost:6379
- **Elasticsearch**: http://localhost:9200
- **Qdrant**: http://localhost:6333
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### 3. Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check Redis connection
docker-compose exec redis redis-cli ping

# Check Elasticsearch
curl http://localhost:9200/_cluster/health

# Check Qdrant
curl http://localhost:6333/health
```

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace nlp-ai
```

### 2. Create Secrets

```bash
# Create API keys secret
kubectl create secret generic nlp-ai-secrets \
  --from-literal=OPENAI_API_KEY=your_openai_api_key \
  --from-literal=ANTHROPIC_API_KEY=your_anthropic_api_key \
  -n nlp-ai
```

### 3. Deploy Services

```bash
# Deploy the application
kubectl apply -f k8s/deployment.yaml

# Deploy services
kubectl apply -f k8s/service.yaml

# Deploy HPA and monitoring
kubectl apply -f k8s/hpa.yaml
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n nlp-ai

# Check services
kubectl get services -n nlp-ai

# Check HPA
kubectl get hpa -n nlp-ai

# Check logs
kubectl logs -f deployment/nlp-ai-service -n nlp-ai
```

### 5. Access the Service

```bash
# Port forward for local access
kubectl port-forward service/nlp-ai-service 8000:80 -n nlp-ai

# Access via LoadBalancer (if configured)
kubectl get service nlp-ai-service-external -n nlp-ai
```

## Redis Caching Configuration

### Cache Configuration

The service uses Redis for caching inference results with the following features:

- **Automatic caching** of LLM responses
- **Configurable TTL** (default: 600 seconds)
- **Cache key generation** based on prompt, model, and parameters
- **Cache statistics** and monitoring

### Cache Endpoints

```bash
# Get cache statistics
curl http://localhost:8000/cache/stats

# Clear cache
curl -X POST http://localhost:8000/cache/clear

# Clear specific pattern
curl -X POST http://localhost:8000/cache/clear?pattern=llm_*
```

### Redis Configuration

The Redis instance is configured with:
- **Memory limit**: 256MB
- **Eviction policy**: allkeys-lru
- **Persistence**: AOF enabled
- **Health checks**: Built-in ping checks

## Monitoring and Observability

### Prometheus Metrics

The service exposes metrics at `/metrics`:

- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request duration
- `llm_requests_total`: Total LLM requests
- `llm_cache_hits_total`: Cache hits
- `llm_cache_misses_total`: Cache misses
- `redis_connections_active`: Active Redis connections

### Grafana Dashboard

Access Grafana at http://localhost:3000 with:
- **Username**: admin
- **Password**: admin (or your configured password)

The dashboard includes:
- Service health metrics
- Request rates and latencies
- Cache hit/miss ratios
- Resource utilization
- Error rates

### Logging

Structured JSON logging with:
- Request/response logging
- Error tracking
- Performance metrics
- Cache operations

## Auto-scaling Configuration

### Horizontal Pod Autoscaler (HPA)

The HPA is configured to scale based on:

- **CPU utilization**: Target 70%
- **Memory utilization**: Target 80%
- **Custom metrics**: HTTP requests per second
- **Cache hit ratio**: Target 80%

### Scaling Behavior

- **Min replicas**: 2
- **Max replicas**: 20
- **Scale up**: 50% increase or 4 pods per minute
- **Scale down**: 10% decrease or 2 pods per 5 minutes

### Resource Limits

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "2000m"
    memory: "4Gi"
```

## Production Considerations

### Security

1. **Use secrets** for API keys
2. **Enable TLS** for external access
3. **Configure network policies**
4. **Use non-root containers**
5. **Enable Pod Security Standards**

### Performance

1. **Optimize resource requests/limits**
2. **Configure proper node affinity**
3. **Use persistent volumes** for data
4. **Enable Redis clustering** for high availability
5. **Configure connection pooling**

### High Availability

1. **Deploy across multiple zones**
2. **Use Pod Disruption Budgets**
3. **Configure health checks**
4. **Set up monitoring alerts**
5. **Implement circuit breakers**

## Troubleshooting

### Common Issues

#### 1. Pod Startup Failures

```bash
# Check pod status
kubectl describe pod <pod-name> -n nlp-ai

# Check logs
kubectl logs <pod-name> -n nlp-ai

# Check events
kubectl get events -n nlp-ai --sort-by='.lastTimestamp'
```

#### 2. Redis Connection Issues

```bash
# Check Redis pod
kubectl get pods -l app=redis -n nlp-ai

# Test Redis connection
kubectl exec -it <redis-pod> -n nlp-ai -- redis-cli ping

# Check Redis logs
kubectl logs <redis-pod> -n nlp-ai
```

#### 3. HPA Not Scaling

```bash
# Check HPA status
kubectl describe hpa nlp-ai-service-hpa -n nlp-ai

# Check metrics server
kubectl top pods -n nlp-ai

# Check custom metrics
kubectl get --raw /apis/custom.metrics.k8s.io/v1beta1
```

#### 4. Cache Performance Issues

```bash
# Check cache stats
curl http://localhost:8000/cache/stats

# Monitor Redis memory
kubectl exec -it <redis-pod> -n nlp-ai -- redis-cli info memory

# Check cache hit ratio
kubectl exec -it <redis-pod> -n nlp-ai -- redis-cli info stats
```

### Performance Tuning

#### Redis Optimization

```bash
# Increase memory limit
kubectl patch deployment redis -n nlp-ai -p '{"spec":{"template":{"spec":{"containers":[{"name":"redis","resources":{"limits":{"memory":"1Gi"}}}]}}}}'

# Adjust eviction policy
kubectl patch deployment redis -n nlp-ai -p '{"spec":{"template":{"spec":{"containers":[{"name":"redis","args":["redis-server","--maxmemory-policy","allkeys-lru","--maxmemory","1gb"]}]}}}}'
```

#### Application Optimization

```bash
# Increase CPU limits
kubectl patch deployment nlp-ai-service -n nlp-ai -p '{"spec":{"template":{"spec":{"containers":[{"name":"api","resources":{"limits":{"cpu":"4000m"}}}]}}}}'

# Adjust HPA targets
kubectl patch hpa nlp-ai-service-hpa -n nlp-ai -p '{"spec":{"metrics":[{"type":"Resource","resource":{"name":"cpu","target":{"averageUtilization":60}}}]}}'
```

## Maintenance

### Regular Tasks

1. **Monitor resource usage**
2. **Check cache hit ratios**
3. **Review error logs**
4. **Update dependencies**
5. **Backup Redis data**

### Updates

```bash
# Update deployment
kubectl set image deployment/nlp-ai-service api=your-registry/nlp-ai-service:v1.1.0 -n nlp-ai

# Rollback if needed
kubectl rollout undo deployment/nlp-ai-service -n nlp-ai

# Check rollout status
kubectl rollout status deployment/nlp-ai-service -n nlp-ai
```

This deployment guide provides a comprehensive approach to running the NLP/AI service in production with proper caching, monitoring, and auto-scaling capabilities.




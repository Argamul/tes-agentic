# Enhanced Observability and Security Setup

This document describes the comprehensive observability, monitoring, and security setup for the NLP AI Microservice.

## 🚀 Features Implemented

### 1. Structured Logging with OpenTelemetry
- **Structured JSON logging** with trace correlation
- **OpenTelemetry instrumentation** for distributed tracing
- **Log correlation** with trace and span IDs
- **Context-aware logging** with service metadata
- **Elastic APM integration** for application performance monitoring

### 2. ELK Stack Integration
- **Elasticsearch** for log storage and search
- **Logstash** for log processing and transformation
- **Kibana** for log visualization and analysis
- **Structured log parsing** with automatic field extraction
- **Real-time log streaming** from the application

### 3. Enhanced Rate Limiting
- **Multiple rate limiting strategies**:
  - Fixed window counter
  - Sliding window
  - Token bucket algorithm
- **User-specific rate limits** with configurable thresholds
- **Redis-backed rate limiting** for distributed systems
- **Rate limit headers** in HTTP responses
- **OpenTelemetry instrumentation** for rate limiting metrics

### 4. Prometheus Metrics
- **Custom Prometheus metrics** for application monitoring
- **System metrics** (CPU, memory, disk usage)
- **HTTP request metrics** (rate, duration, status codes)
- **OpenTelemetry metrics** integration
- **Metrics aggregation** by endpoint, method, and status code

### 5. Grafana Dashboard
- **Pre-configured dashboard** for the NLP AI microservice
- **Real-time metrics visualization**
- **System health monitoring**
- **Performance trend analysis**
- **Alert configuration** support

### 6. TLS/SSL Security
- **Automatic certificate generation** for development
- **Self-signed certificate support** with SAN (Subject Alternative Names)
- **Secure SSL context configuration**
- **Certificate validation** and monitoring
- **TLS version enforcement** (TLS 1.2+)
- **Secure cipher suite configuration**

## 🛠️ Setup Instructions

### Prerequisites
- Docker and Docker Compose
- Python 3.8+ (for local development)
- OpenSSL (for certificate generation)

### 1. Environment Configuration

Copy the example environment file and configure your settings:

```bash
cp env.example .env
```

Key configuration variables:

```bash
# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:14268/api/traces
OTEL_METRICS_ENABLED=true
SERVICE_NAME=nlp-ai-microservice
SERVICE_VERSION=1.0.0

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_STRATEGY=fixed_window

# TLS
TLS_ENABLED=false  # Set to true for HTTPS
TLS_CERT_FILE=./certs/server.crt
TLS_KEY_FILE=./certs/server.key

# ELK Stack
ELASTIC_APM_ENABLED=false
ELASTIC_APM_SERVER_URL=http://elasticsearch:8200
```

### 2. Start the Complete Stack

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Check service health
curl http://localhost:8000/health
```

### 3. Access Monitoring Dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **Kibana**: http://localhost:5601
- **Elasticsearch**: http://localhost:9200

## 📊 Monitoring Endpoints

### Application Endpoints
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /metrics/summary` - Metrics summary
- `GET /rate-limit/status` - Rate limit status
- `GET /tls/status` - TLS certificate status
- `POST /tls/setup` - Setup TLS certificates

### Example Usage

```bash
# Check application health
curl http://localhost:8000/health

# Get metrics summary
curl http://localhost:8000/metrics/summary

# Check rate limit status
curl http://localhost:8000/rate-limit/status?client_id=test-user

# Validate TLS certificates
curl http://localhost:8000/tls/status

# Setup TLS for development
curl -X POST http://localhost:8000/tls/setup
```

## 🔧 Configuration Options

### Rate Limiting Strategies

#### Fixed Window Counter
```bash
RATE_LIMIT_STRATEGY=fixed_window
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

#### Sliding Window
```bash
RATE_LIMIT_STRATEGY=sliding_window
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

#### Token Bucket
```bash
RATE_LIMIT_STRATEGY=token_bucket
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

### User-Specific Rate Limits
```bash
# Format: user_id:limit:window_seconds
RATE_LIMIT_USER_LIMITS=admin-user:1000:60,teacher-user:500:60,student-user:100:60
```

### TLS Configuration
```bash
# Enable TLS
TLS_ENABLED=true

# Certificate files
TLS_CERT_FILE=./certs/server.crt
TLS_KEY_FILE=./certs/server.key
TLS_CA_FILE=./certs/ca.crt

# Security settings
TLS_MIN_VERSION=TLSv1.2
TLS_VERIFY_CLIENT=false
TLS_CERT_VALIDATION=true
```

## 📈 Grafana Dashboard

The included Grafana dashboard provides:

1. **HTTP Request Rate** - Requests per second by method and endpoint
2. **HTTP Request Duration** - 95th and 50th percentile response times
3. **Active Connections** - Current active HTTP connections
4. **CPU Usage** - System CPU utilization percentage
5. **Memory Usage** - System memory usage (used vs total)
6. **Status Code Distribution** - HTTP status code breakdown
7. **Custom OpenTelemetry Metrics** - Application-specific metrics

### Dashboard Import

The dashboard is automatically imported via the `grafana/dashboard.json` file.

## 🔍 Log Analysis

### Structured Log Format

Logs are automatically structured with the following fields:

```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "level": "INFO",
  "logger": "nlp-ai-microservice",
  "message": "Request processed successfully",
  "service": "nlp-ai-microservice",
  "environment": "development",
  "trace_id": "abc123def456",
  "span_id": "def456ghi789",
  "module": "main",
  "function": "health_check",
  "line": 367,
  "user_id": "user-123",
  "request_id": "req-456"
}
```

### Log Correlation

All logs are automatically correlated with OpenTelemetry traces using:
- `trace_id` - Unique trace identifier
- `span_id` - Unique span identifier within the trace

### Kibana Queries

Example Kibana queries for log analysis:

```json
// Find all errors in the last hour
{
  "query": {
    "bool": {
      "must": [
        {"term": {"level": "ERROR"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}

// Find requests for a specific user
{
  "query": {
    "term": {"user_id": "user-123"}
  }
}

// Find requests by trace ID
{
  "query": {
    "term": {"trace_id": "abc123def456"}
  }
}
```

## 🚨 Alerting

### Prometheus Alerts

Configure alerts in Prometheus for:

- High error rate (> 5% errors)
- High response time (> 1 second)
- High CPU usage (> 80%)
- High memory usage (> 85%)
- Rate limit violations

### Grafana Alerts

Set up Grafana alerts for:
- Service downtime
- Performance degradation
- Resource exhaustion
- Security events

## 🔒 Security Features

### TLS/SSL
- **Automatic certificate generation** for development
- **Secure cipher suites** (ECDHE, AES-GCM, ChaCha20)
- **TLS version enforcement** (minimum TLS 1.2)
- **Certificate validation** and monitoring
- **SAN support** for multiple hostnames/IPs

### Rate Limiting
- **IP-based rate limiting** for anonymous users
- **User-based rate limiting** for authenticated users
- **API key-based rate limiting** for external access
- **Configurable rate limits** per user type
- **Redis-backed** for distributed rate limiting

### Observability Security
- **Structured logging** without sensitive data exposure
- **Trace correlation** for security event tracking
- **Metrics collection** for security monitoring
- **Audit logging** for compliance

## 🐛 Troubleshooting

### Common Issues

1. **Certificate Generation Fails**
   ```bash
   # Check certificate directory permissions
   mkdir -p certs
   chmod 755 certs
   ```

2. **Rate Limiting Not Working**
   ```bash
   # Check Redis connection
   docker-compose logs redis
   
   # Verify rate limit configuration
   curl http://localhost:8000/rate-limit/status
   ```

3. **Metrics Not Appearing**
   ```bash
   # Check Prometheus configuration
   curl http://localhost:9090/api/v1/targets
   
   # Verify metrics endpoint
   curl http://localhost:8000/metrics
   ```

4. **Logs Not Reaching Elasticsearch**
   ```bash
   # Check Logstash status
   docker-compose logs logstash
   
   # Verify Elasticsearch connectivity
   curl http://localhost:9200/_cluster/health
   ```

### Debug Commands

```bash
# Check all service health
docker-compose ps

# View application logs
docker-compose logs -f api

# Check Redis connectivity
docker-compose exec redis redis-cli ping

# Verify certificate validity
openssl x509 -in certs/server.crt -text -noout

# Test rate limiting
for i in {1..10}; do curl http://localhost:8000/health; done
```

## 📚 Additional Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [ELK Stack Documentation](https://www.elastic.co/guide/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 🤝 Contributing

When adding new features, ensure:
1. Add appropriate logging with context
2. Include OpenTelemetry instrumentation
3. Add relevant metrics
4. Update rate limiting if needed
5. Test TLS configuration
6. Update documentation

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.


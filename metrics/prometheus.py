import os
import time
import psutil
from typing import Dict, Any
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
from fastapi import Request, Response

from observability.otel_setup import get_meter


# Custom Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code', 'service']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'service'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

ACTIVE_CONNECTIONS = Gauge(
    'http_active_connections',
    'Number of active HTTP connections',
    ['service']
)

SYSTEM_INFO = Info(
    'system_info',
    'System information',
    ['service', 'version', 'environment']
)

MEMORY_USAGE = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes',
    ['service', 'type']
)

CPU_USAGE = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage',
    ['service']
)

# OpenTelemetry metrics
otel_meter = get_meter("prometheus_metrics")

# Custom metrics
request_counter = otel_meter.create_counter(
    name="custom_requests_total",
    description="Custom request counter",
    unit="1"
)

request_duration_histogram = otel_meter.create_histogram(
    name="custom_request_duration_seconds",
    description="Custom request duration",
    unit="s"
)

system_metrics_gauge = otel_meter.create_up_down_counter(
    name="custom_system_metrics",
    description="Custom system metrics",
    unit="1"
)


def setup_custom_metrics():
    """Setup custom metrics with labels"""
    service_name = os.getenv("SERVICE_NAME", "nlp-ai-microservice")
    service_version = os.getenv("SERVICE_VERSION", "1.0.0")
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Set system info
    SYSTEM_INFO.labels(
        service=service_name,
        version=service_version,
        environment=environment
    ).info({
        'python_version': os.sys.version,
        'platform': os.name,
    })


def update_system_metrics():
    """Update system metrics"""
    service_name = os.getenv("SERVICE_NAME", "nlp-ai-microservice")
    
    try:
        # Memory usage
        memory = psutil.virtual_memory()
        MEMORY_USAGE.labels(service=service_name, type="total").set(memory.total)
        MEMORY_USAGE.labels(service=service_name, type="available").set(memory.available)
        MEMORY_USAGE.labels(service=service_name, type="used").set(memory.used)
        MEMORY_USAGE.labels(service=service_name, type="cached").set(getattr(memory, 'cached', 0))
        MEMORY_USAGE.labels(service=service_name, type="buffers").set(getattr(memory, 'buffers', 0))
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        CPU_USAGE.labels(service=service_name).set(cpu_percent)
        
        # OpenTelemetry system metrics
        system_metrics_gauge.add(cpu_percent, {"metric_type": "cpu_usage", "service": service_name})
        system_metrics_gauge.add(memory.percent, {"metric_type": "memory_usage", "service": service_name})
        
    except Exception as e:
        print(f"Failed to update system metrics: {e}")


def setup_metrics(app) -> None:
    """Enhanced Prometheus metrics setup"""
    endpoint = os.getenv("PROMETHEUS_METRICS_ENDPOINT", "/metrics")
    service_name = os.getenv("SERVICE_NAME", "nlp-ai-microservice")
    
    # Setup custom metrics
    setup_custom_metrics()
    
    # Configure FastAPI instrumentator with custom metrics
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        excluded_handlers=[endpoint, "/health", "/docs", "/openapi.json", "/redoc"],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
        env_var_name="ENABLE_METRICS",
        inprogress_help="Number of HTTP requests currently being processed",
    )
    
    # Add custom metrics
    instrumentator.add(metrics.default())
    
    # Custom request counter
    @instrumentator.add_metric(
        name="custom_request_counter",
        description="Custom request counter with additional labels",
        labels={
            "method": lambda r: r.method,
            "endpoint": lambda r: r.url.path,
            "service": lambda r: service_name,
        }
    )
    def custom_request_counter(response: Response, request: Request) -> int:
        return 1
    
    # Custom response time histogram
    @instrumentator.add_metric(
        name="custom_response_time",
        description="Custom response time histogram",
        labels={
            "method": lambda r: r.method,
            "endpoint": lambda r: r.url.path,
            "service": lambda r: service_name,
        }
    )
    def custom_response_time(response: Response, request: Request) -> float:
        # Get request start time from request state
        start_time = getattr(request.state, "start_time", time.time())
        return time.time() - start_time
    
    # Request processing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        request.state.start_time = start_time
        
        # Update active connections
        ACTIVE_CONNECTIONS.labels(service=service_name).inc()
        
        response = await call_next(request)
        
        # Update metrics
        duration = time.time() - start_time
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            service=service_name
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path,
            service=service_name
        ).observe(duration)
        
        # OpenTelemetry metrics
        request_counter.add(1, {
            "method": request.method,
            "endpoint": request.url.path,
            "status_code": str(response.status_code),
            "service": service_name
        })
        
        request_duration_histogram.record(duration, {
            "method": request.method,
            "endpoint": request.url.path,
            "service": service_name
        })
        
        # Decrement active connections
        ACTIVE_CONNECTIONS.labels(service=service_name).dec()
        
        return response
    
    # System metrics update endpoint
    @app.get("/metrics/system")
    async def system_metrics():
        """Get system metrics"""
        update_system_metrics()
        return generate_latest()
    
    # Instrument the app
    instrumentator.instrument(app).expose(
        app, 
        include_in_schema=False, 
        endpoint=endpoint
    )


def get_metrics_summary() -> Dict[str, Any]:
    """Get a summary of current metrics"""
    service_name = os.getenv("SERVICE_NAME", "nlp-ai-microservice")
    
    try:
        # Get system metrics
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        return {
            "service": service_name,
            "timestamp": time.time(),
            "system": {
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent
                },
                "cpu": {
                    "percent": cpu_percent
                }
            },
            "metrics_endpoint": os.getenv("PROMETHEUS_METRICS_ENDPOINT", "/metrics")
        }
    except Exception as e:
        return {
            "service": service_name,
            "timestamp": time.time(),
            "error": str(e)
        }




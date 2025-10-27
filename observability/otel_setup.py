import os
import logging
import json
import sys
from typing import Optional, Dict, Any
from datetime import datetime

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.elasticsearch import ElasticsearchInstrumentor

from pythonjsonlogger import jsonlogger
from loguru import logger
import elasticapm


class StructuredLogHandler(logging.Handler):
    """Custom handler for structured logging with OpenTelemetry correlation"""
    
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name
        self.environment = os.getenv("ENVIRONMENT", "development")
    
    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Get current span context for correlation
            span = trace.get_current_span()
            span_context = span.get_span_context() if span.is_recording() else None
            
            # Build structured log entry
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "service": self.service_name,
                "environment": self.environment,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            
            # Add OpenTelemetry trace correlation
            if span_context and span_context.is_valid:
                log_entry.update({
                    "trace_id": f"{span_context.trace_id:032x}",
                    "span_id": f"{span_context.span_id:016x}",
                })
            
            # Add exception info if present
            if record.exc_info:
                log_entry["exception"] = {
                    "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                    "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                    "traceback": self.format(record) if record.exc_info[2] else None,
                }
            
            # Add extra fields from record
            for key, value in record.__dict__.items():
                if key not in {'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'getMessage', 'exc_info', 
                              'exc_text', 'stack_info'}:
                    log_entry[key] = value
            
            # Output as JSON
            print(json.dumps(log_entry), file=sys.stdout)
            
        except Exception:
            # Fallback to basic logging if structured logging fails
            self.handleError(record)


def configure_elastic_apm(service_name: str) -> None:
    """Configure Elastic APM for additional observability"""
    apm_enabled = os.getenv("ELASTIC_APM_ENABLED", "false").lower() == "true"
    if not apm_enabled:
        return
    
    elasticapm.configure(
        service_name=service_name,
        service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
        environment=os.getenv("ENVIRONMENT", "development"),
        server_url=os.getenv("ELASTIC_APM_SERVER_URL", "http://localhost:8200"),
        secret_token=os.getenv("ELASTIC_APM_SECRET_TOKEN"),
        debug=os.getenv("ENVIRONMENT", "development") == "development",
    )


def configure_json_logging(service_name: str) -> None:
    """Enhanced structured logging configuration"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add structured log handler
    structured_handler = StructuredLogHandler(service_name)
    structured_handler.setLevel(getattr(logging, log_level, logging.INFO))
    root_logger.addHandler(structured_handler)
    
    # Configure loguru for additional structured logging
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        level=log_level,
        serialize=True,
        backtrace=True,
        diagnose=True,
        filter=lambda record: {
            **record,
            "service": service_name,
            "environment": os.getenv("ENVIRONMENT", "development"),
        }
    )
    
    # Configure Elastic APM if enabled
    configure_elastic_apm(service_name)


def init_tracing(service_name: str, app=None) -> Optional[TracerProvider]:
    """Enhanced OpenTelemetry tracing setup"""
    # Configure resource attributes
    resource_attrs = {
        "service.name": service_name,
        "service.namespace": os.getenv("OTEL_SERVICE_NAMESPACE", "nlp-ai"),
        "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    }
    
    # Add container/pod information if available
    if os.getenv("KUBERNETES_NAMESPACE"):
        resource_attrs.update({
            "k8s.namespace.name": os.getenv("KUBERNETES_NAMESPACE"),
            "k8s.pod.name": os.getenv("HOSTNAME", "unknown"),
        })
    
    resource = Resource.create(resource_attrs)
    
    # Configure trace provider
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    
    if otlp_endpoint:
        # Configure with OTLP exporter
        trace_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers=os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""),
        )
        span_processor = BatchSpanProcessor(
            trace_exporter,
            max_export_batch_size=512,
            export_timeout_millis=30000,
            schedule_delay_millis=5000,
        )
        provider = TracerProvider(resource=resource, span_processors=[span_processor])
    else:
        # Configure without exporter for local development
        provider = TracerProvider(resource=resource)
    
    trace.set_tracer_provider(provider)
    
    # Configure metrics if enabled
    metrics_enabled = os.getenv("OTEL_METRICS_ENABLED", "false").lower() == "true"
    if metrics_enabled:
        otlp_metrics_endpoint = os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT") or otlp_endpoint
        if otlp_metrics_endpoint:
            metric_exporter = OTLPMetricExporter(
                endpoint=otlp_metrics_endpoint,
                headers=os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""),
            )
            metric_reader = PeriodicExportingMetricReader(
                metric_exporter,
                export_interval_millis=30000,
            )
            meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
            metrics.set_meter_provider(meter_provider)
    
    # Configure instrumentations
    LoggingInstrumentor().instrument(
        set_logging_format=True,
        logging_format="%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] - %(message)s"
    )
    
    HTTPXClientInstrumentor().instrument()
    
    try:
        RedisInstrumentor().instrument()
    except Exception as e:
        logger.warning(f"Failed to instrument Redis: {e}")
    
    try:
        ElasticsearchInstrumentor().instrument()
    except Exception as e:
        logger.warning(f"Failed to instrument Elasticsearch: {e}")
    
    # Instrument FastAPI app if provided
    if app is not None:
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="health,metrics,docs,openapi.json,redoc",
            server_request_hook=lambda span, scope: span.set_attribute("http.route", scope.get("route", {}).get("path", "unknown")),
            client_request_hook=lambda span, scope: span.set_attribute("http.route", scope.get("route", {}).get("path", "unknown")),
        )
        app.add_middleware(OpenTelemetryMiddleware)
    
    return trace.get_tracer_provider()


def get_tracer(name: str = None) -> trace.Tracer:
    """Get a tracer instance"""
    return trace.get_tracer(name or __name__)


def get_meter(name: str = None) -> metrics.Meter:
    """Get a meter instance"""
    return metrics.get_meter(name or __name__)


class LogContext:
    """Context manager for adding structured logging context"""
    
    def __init__(self, **context):
        self.context = context
        self.original_context = {}
    
    def __enter__(self):
        # Store original context
        for key in self.context:
            if hasattr(logger.context, key):
                self.original_context[key] = getattr(logger.context, key)
            setattr(logger.context, key, self.context[key])
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original context
        for key in self.context:
            if key in self.original_context:
                setattr(logger.context, key, self.original_context[key])
            elif hasattr(logger.context, key):
                delattr(logger.context, key)


def log_with_context(level: str, message: str, **context):
    """Log with additional context"""
    with LogContext(**context):
        getattr(logger, level.lower())(message)




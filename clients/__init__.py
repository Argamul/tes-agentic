"""Client modules for external services (User, Question, API Gateway).

Provides:
- Service discovery helpers
- Async REST clients using httpx
- Optional gRPC client wrappers (imports guarded if stubs are not available)
"""

__all__ = [
    "service_discovery",
    "api_clients",
    "grpc_clients",
]



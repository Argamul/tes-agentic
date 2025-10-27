from __future__ import annotations

import os
import time
import hashlib
from typing import Iterable, Optional, Dict, Any
from enum import Enum

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from cache.redis_cache import get_redis_client
from observability.otel_setup import get_tracer, log_with_context


class RateLimitStrategy(Enum):
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


class RateLimitConfig:
    """Configuration for rate limiting"""
    
    def __init__(self):
        self.default_limit = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self.default_window = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
        self.strategy = RateLimitStrategy(os.getenv("RATE_LIMIT_STRATEGY", "fixed_window"))
        self.exempt_paths = os.getenv("RATE_LIMIT_EXEMPT_PATHS", "/health,/metrics,/docs,/openapi.json,/redoc").split(",")
        self.burst_limit = int(os.getenv("RATE_LIMIT_BURST", "10"))
        self.user_limits = self._parse_user_limits()
    
    def _parse_user_limits(self) -> Dict[str, Dict[str, int]]:
        """Parse user-specific rate limits from environment"""
        # Format: "user_id:limit:window,user_id2:limit2:window2"
        user_limits_str = os.getenv("RATE_LIMIT_USER_LIMITS", "")
        if not user_limits_str:
            return {}
        
        limits = {}
        for limit_str in user_limits_str.split(","):
            parts = limit_str.strip().split(":")
            if len(parts) == 3:
                user_id, limit, window = parts
                limits[user_id] = {
                    "limit": int(limit),
                    "window": int(window)
                }
        return limits
    
    def get_limit_for_user(self, user_id: str = None) -> tuple[int, int]:
        """Get rate limit for a specific user"""
        if user_id and user_id in self.user_limits:
            config = self.user_limits[user_id]
            return config["limit"], config["window"]
        return self.default_limit, self.default_window


# Global rate limit configuration
rate_limit_config = RateLimitConfig()

# SlowAPI Limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    default_limits=[f"{rate_limit_config.default_limit}/{rate_limit_config.default_window}s"]
)


def _is_exempt_path(path: str) -> bool:
    """Check if path is exempt from rate limiting"""
    path = path.rstrip("/") or "/"
    return any((path == e.rstrip("/") or path.startswith(e.rstrip("/"))) for e in rate_limit_config.exempt_paths if e)


def _get_client_identifier(request: Request) -> str:
    """Get client identifier for rate limiting"""
    # Try to get user ID from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    
    # Try to get API key from request state
    api_key = getattr(request.state, "api_key", None)
    if api_key:
        # Use hash of API key for privacy
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return f"api_key:{api_key_hash}"
    
    # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


async def _check_rate_limit_redis(client_id: str, limit: int, window: int) -> tuple[bool, int, int]:
    """Check rate limit using Redis"""
    redis = get_redis_client()
    if redis is None:
        return True, 0, 0  # Allow if Redis is unavailable
    
    current_time = int(time.time())
    
    if rate_limit_config.strategy == RateLimitStrategy.FIXED_WINDOW:
        # Fixed window counter
        window_start = current_time - (current_time % window)
        key = f"ratelimit:fixed:{client_id}:{window_start}"
        
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)

        return count <= limit, count, limit
    
    elif rate_limit_config.strategy == RateLimitStrategy.SLIDING_WINDOW:
        # Sliding window using sorted sets
        key = f"ratelimit:sliding:{client_id}"
        
        # Remove expired entries
        await redis.zremrangebyscore(key, 0, current_time - window)
        
        # Count current entries
        count = await redis.zcard(key)
        
        if count < limit:
            # Add current request
            await redis.zadd(key, {str(current_time): current_time})
            await redis.expire(key, window)
            return True, count + 1, limit
        else:
            return False, count, limit
    
    elif rate_limit_config.strategy == RateLimitStrategy.TOKEN_BUCKET:
        # Token bucket algorithm
        bucket_key = f"ratelimit:bucket:{client_id}"
        last_refill_key = f"ratelimit:last_refill:{client_id}"
        
        # Get current tokens and last refill time
        pipe = redis.pipeline()
        pipe.hget(bucket_key, "tokens")
        pipe.hget(last_refill_key, "timestamp")
        results = await pipe.execute()
        
        current_tokens = int(results[0] or limit)
        last_refill = float(results[1] or current_time)
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = current_time - last_refill
        tokens_to_add = min(limit, int(time_elapsed * limit / window))
        
        # Refill bucket
        new_tokens = min(limit, current_tokens + tokens_to_add)
        
        if new_tokens > 0:
            # Consume one token
            new_tokens -= 1
            await redis.hset(bucket_key, "tokens", new_tokens)
            await redis.hset(last_refill_key, "timestamp", current_time)
            await redis.expire(bucket_key, window)
            await redis.expire(last_refill_key, window)
            return True, limit - new_tokens, limit
        else:
            return False, limit - new_tokens, limit
    
    return True, 0, limit


class EnhancedRateLimitMiddleware(BaseHTTPMiddleware):
    """Enhanced rate limiting middleware with multiple strategies and user-based limits"""
    
    def __init__(self, app):
        super().__init__(app)
        self.tracer = get_tracer("rate_limit_middleware")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for exempt paths
        if _is_exempt_path(request.url.path):
            return await call_next(request)
        
        with self.tracer.start_as_current_span("rate_limit_check") as span:
            # Get client identifier
            client_id = _get_client_identifier(request)
            span.set_attribute("client_id", client_id)
            span.set_attribute("request_path", request.url.path)
            
            # Get user ID if available for user-specific limits
            user_id = getattr(request.state, "user_id", None)
            limit, window = rate_limit_config.get_limit_for_user(user_id)
            
            span.set_attribute("rate_limit", limit)
            span.set_attribute("rate_window", window)
            span.set_attribute("strategy", rate_limit_config.strategy.value)
            
            # Check rate limit
            allowed, current_count, max_count = await _check_rate_limit_redis(client_id, limit, window)
            
            span.set_attribute("rate_limit_allowed", allowed)
            span.set_attribute("current_count", current_count)
            span.set_attribute("max_count", max_count)
            
            if not allowed:
                # Rate limit exceeded
                span.set_attribute("rate_limit_exceeded", True)
                log_with_context(
                    "warning",
                    f"Rate limit exceeded for {client_id}",
                    client_id=client_id,
                    current_count=current_count,
                    max_count=max_count,
                    window=window,
                    path=request.url.path,
                    user_id=user_id
                )
                
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                        "current_count": current_count,
                        "max_count": max_count,
                        "window_seconds": window,
                        "retry_after_seconds": window,
                        "strategy": rate_limit_config.strategy.value
                    },
                    headers={
                        "Retry-After": str(window),
                        "X-RateLimit-Limit": str(max_count),
                        "X-RateLimit-Remaining": str(max(0, max_count - current_count)),
                        "X-RateLimit-Reset": str(int(time.time()) + window)
                    }
                )
            
            # Add rate limit headers to successful responses
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(max_count)
            response.headers["X-RateLimit-Remaining"] = str(max(0, max_count - current_count))
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window)
            
            return response


# Backward compatibility
RateLimitMiddleware = EnhancedRateLimitMiddleware


def setup_rate_limiting(app):
    """Setup rate limiting with SlowAPI and custom middleware"""
    # Add SlowAPI middleware for decorator-based rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    # Add custom middleware for path-based rate limiting
    app.add_middleware(EnhancedRateLimitMiddleware)


def get_rate_limit_status(client_id: str = None) -> Dict[str, Any]:
    """Get current rate limit status for debugging"""
    if not client_id:
        return {"error": "client_id is required"}
    
    limit, window = rate_limit_config.get_limit_for_user(client_id)
    
    return {
        "client_id": client_id,
        "limit": limit,
        "window_seconds": window,
        "strategy": rate_limit_config.strategy.value,
        "exempt_paths": rate_limit_config.exempt_paths
    }




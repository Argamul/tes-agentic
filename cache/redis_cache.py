import os
import json
import hashlib
from typing import Any, Optional

from redis import asyncio as aioredis


_redis_client: Optional[aioredis.Redis] = None


def _get_ttl_seconds() -> int:
    try:
        return int(os.getenv("REDIS_CACHE_TTL_SECONDS", "600"))
    except ValueError:
        return 600


def get_redis_client() -> Optional[aioredis.Redis]:
    global _redis_client
    redis_url = os.getenv("REDIS_URL") or os.getenv("REDIS_HOST")
    if not redis_url:
        return None

    # Support specifying host/port separately
    if not redis_url.startswith("redis://") and not redis_url.startswith("rediss://"):
        host = os.getenv("REDIS_HOST", "localhost")
        port = os.getenv("REDIS_PORT", "6379")
        db = os.getenv("REDIS_DB", "0")
        password = os.getenv("REDIS_PASSWORD")
        scheme = "rediss" if os.getenv("REDIS_TLS", "false").lower() in {"1", "true", "yes"} else "redis"
        auth = f":{password}@" if password else ""
        redis_url = f"{scheme}://{auth}{host}:{port}/{db}"

    if _redis_client is None:
        _redis_client = aioredis.from_url(redis_url, decode_responses=True)
    return _redis_client


def make_cache_key(prefix: str, *parts: Any) -> str:
    hasher = hashlib.sha256()
    for part in parts:
        try:
            encoded = json.dumps(part, sort_keys=True, default=str)
        except TypeError:
            encoded = str(part)
        hasher.update(encoded.encode("utf-8"))
    digest = hasher.hexdigest()
    return f"{prefix}:{digest}"


async def cache_get_text(key: str) -> Optional[str]:
    client = get_redis_client()
    if not client:
        return None
    return await client.get(key)


async def cache_set_text(key: str, value: str, ttl_seconds: Optional[int] = None) -> None:
    client = get_redis_client()
    if not client:
        return
    await client.set(key, value, ex=ttl_seconds or _get_ttl_seconds())


async def cache_get_json(key: str) -> Optional[Any]:
    raw = await cache_get_text(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def cache_set_json(key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
    try:
        payload = json.dumps(value)
    except TypeError:
        # Fallback to string representation
        payload = json.dumps(str(value))
    await cache_set_text(key, payload, ttl_seconds)





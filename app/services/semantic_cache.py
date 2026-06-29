from __future__ import annotations

import redis.asyncio as aioredis

from app.config import settings

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def get_cached(query: str) -> str | None:
    """Return cached response for *query*, or None on miss."""
    raise NotImplementedError


async def set_cached(query: str, response: str, ttl: int = 3600) -> None:
    """Cache *response* for *query* with *ttl* seconds expiry."""
    raise NotImplementedError


async def invalidate(query: str) -> None:
    """Delete cached entry for *query*."""
    raise NotImplementedError

from __future__ import annotations

import redis.asyncio as aioredis

from app.config import settings


class RedisCache:
    """Semantic response cache backed by Redis."""

    def __init__(self) -> None:
        self._client: aioredis.Redis = aioredis.from_url(
            settings.redis_url, decode_responses=True
        )

    async def get_cached(self, query: str) -> str | None:
        """Return cached response for *query*, or None on miss."""
        raise NotImplementedError

    async def set_cached(self, query: str, response: str, ttl: int = 3600) -> None:
        """Cache *response* for *query* with *ttl* seconds expiry."""
        raise NotImplementedError

    async def invalidate(self, query: str) -> None:
        """Delete cached entry for *query*."""
        raise NotImplementedError

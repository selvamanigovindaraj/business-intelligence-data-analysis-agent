from __future__ import annotations

import hashlib
from typing import cast

import redis.asyncio as aioredis

from app.config import settings


class RedisCache:
    """Semantic response cache backed by Redis."""

    def __init__(self) -> None:
        self._client: aioredis.Redis = aioredis.from_url(
            settings.redis_url, decode_responses=True
        )

    def _key(self, query: str) -> str:
        return hashlib.sha256(query.encode()).hexdigest()

    async def get_cached(self, query: str) -> str | None:
        """Return cached response for *query*, or None on miss."""
        # cast: decode_responses=True guarantees str, but aioredis types still include bytes
        return cast(str | None, await self._client.get(self._key(query)))

    async def set_cached(self, query: str, response: str, ttl: int = 3600) -> None:
        """Cache *response* for *query* with *ttl* seconds expiry."""
        await self._client.setex(self._key(query), ttl, response)

    async def invalidate(self, query: str) -> None:
        """Delete cached entry for *query*."""
        await self._client.delete(self._key(query))

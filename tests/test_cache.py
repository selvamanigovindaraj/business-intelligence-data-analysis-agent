from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.semantic_cache import RedisCache


@pytest.mark.asyncio
async def test_cache_miss_returns_none() -> None:
    with patch("app.services.semantic_cache.aioredis.from_url") as mock_from_url:
        mock_client = AsyncMock()
        mock_client.get.return_value = None
        mock_from_url.return_value = mock_client

        cache = RedisCache()
        result = await cache.get_cached("unknown query")

        assert result is None
        mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_cache_hit_returns_value() -> None:
    with patch("app.services.semantic_cache.aioredis.from_url") as mock_from_url:
        mock_client = AsyncMock()
        mock_client.get.return_value = "cached response"
        mock_from_url.return_value = mock_client

        cache = RedisCache()
        result = await cache.get_cached("known query")

        assert result == "cached response"

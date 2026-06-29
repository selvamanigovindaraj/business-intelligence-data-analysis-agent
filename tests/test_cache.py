from __future__ import annotations

import pytest

from app.services.semantic_cache import get_cached, set_cached


@pytest.mark.asyncio
async def test_cache_miss_returns_none() -> None:
    # TODO: mock Redis, assert get_cached returns None on miss
    raise NotImplementedError


@pytest.mark.asyncio
async def test_cache_hit_returns_value() -> None:
    # TODO: set then get, assert value matches
    raise NotImplementedError

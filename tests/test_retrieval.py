from __future__ import annotations

import pytest

from app.components.retriever import PineconeRetriever


@pytest.mark.asyncio
async def test_retrieve_returns_documents() -> None:
    # TODO: mock Pinecone client and assert retrieve() returns Document list
    raise NotImplementedError


@pytest.mark.asyncio
async def test_add_documents_upserts() -> None:
    # TODO: assert add_documents() calls pinecone upsert
    raise NotImplementedError

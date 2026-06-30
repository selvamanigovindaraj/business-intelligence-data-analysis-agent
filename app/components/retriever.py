from __future__ import annotations

import asyncio
from uuid import uuid4

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from pydantic import SecretStr
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.config import settings

EMBED_DIM: int = settings.embed_dim


class QdrantRetriever:
    """Semantic retriever backed by Qdrant."""

    def __init__(self, collection_name: str = settings.qdrant_collection_name) -> None:
        self._collection_name = collection_name
        self._qdrant = QdrantClient(url=settings.qdrant_url)
        # ponytail: QdrantVectorStore has no native async — all ops are run_in_executor.
        # validate_collection_config=False skips get_collection + embed_documents("dummy_text")
        # at init time; callers must call ensure_collection() before first write.
        self._store = QdrantVectorStore(
            client=self._qdrant,
            collection_name=collection_name,
            embedding=OpenAIEmbeddings(
                model=settings.embed_model,
                base_url=settings.embed_base_url,
                api_key=SecretStr(settings.nebius_api_key),
                # Nebius does not accept pre-tokenized input; skip all tokenization paths
                tiktoken_enabled=False,
                check_embedding_ctx_length=False,
            ),
            validate_collection_config=False,
        )

    async def ensure_collection(self, vector_size: int = EMBED_DIM) -> None:
        exists = await asyncio.to_thread(self._qdrant.collection_exists, self._collection_name)
        if not exists:
            await asyncio.to_thread(
                self._qdrant.create_collection,
                collection_name=self._collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    async def retrieve(self, query: str, k: int = 6) -> list[Document]:
        return await self._store.asimilarity_search(query, k=k)

    async def add_documents(self, documents: list[Document]) -> list[str]:
        ids = [str(uuid4()) for _ in documents]
        return await self._store.aadd_documents(documents, ids=ids)

    async def delete_documents(self, ids: list[str]) -> None:
        await self._store.adelete(ids=ids)

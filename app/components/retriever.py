from __future__ import annotations

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from pydantic import SecretStr
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import settings

# ponytail: text-embedding-3-small dim; update if EMBED_MODEL changes
EMBED_DIM = 1536


class QdrantRetriever:
    """Semantic retriever backed by Qdrant."""

    def __init__(self, collection_name: str = settings.qdrant_collection_name) -> None:
        self._client = AsyncQdrantClient(url=settings.qdrant_url)
        self._collection_name = collection_name
        self._embeddings = OpenAIEmbeddings(
            model=settings.embed_model,
            base_url=settings.embed_base_url,
            api_key=SecretStr(settings.embed_api_key),
        )
        self._store = QdrantVectorStore(
            client=self._client,
            collection_name=collection_name,
            embedding=self._embeddings,
        )

    async def ensure_collection(self, vector_size: int = EMBED_DIM) -> None:
        existing = {c.name for c in (await self._client.get_collections()).collections}
        if self._collection_name not in existing:
            await self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    async def retrieve(self, query: str, k: int = 6) -> list[Document]:
        return await self._store.asimilarity_search(query, k=k)

    async def add_documents(self, documents: list[Document]) -> None:
        await self._store.aadd_documents(documents)

    async def delete_documents(self, ids: list[str]) -> None:
        await self._store.adelete(ids)

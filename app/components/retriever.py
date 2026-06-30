from __future__ import annotations

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointIdsList, PointStruct, VectorParams

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

    async def ensure_collection(self, vector_size: int = EMBED_DIM) -> None:
        existing = {c.name for c in (await self._client.get_collections()).collections}
        if self._collection_name not in existing:
            await self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    async def retrieve(self, query: str, k: int = 6) -> list[Document]:
        vector = await self._embeddings.aembed_query(query)
        response = await self._client.query_points(
            collection_name=self._collection_name,
            query=vector,
            limit=k,
        )
        return [
            Document(
                page_content=(point.payload or {}).get("text", ""),
                metadata={key: val for key, val in (point.payload or {}).items() if key != "text"},
            )
            for point in response.points
        ]

    async def add_documents(self, documents: list[Document]) -> None:
        texts = [doc.page_content for doc in documents]
        vectors = await self._embeddings.aembed_documents(texts)
        points = [
            PointStruct(
                id=i,
                vector=vec,
                payload={"text": doc.page_content, **doc.metadata},
            )
            for i, (doc, vec) in enumerate(zip(documents, vectors, strict=True))
        ]
        await self._client.upsert(collection_name=self._collection_name, points=points)

    async def delete_documents(self, ids: list[int]) -> None:
        await self._client.delete(
            collection_name=self._collection_name,
            points_selector=PointIdsList(points=ids),  # type: ignore[arg-type]
        )

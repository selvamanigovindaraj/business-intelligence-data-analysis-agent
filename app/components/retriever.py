from __future__ import annotations

from langchain_core.documents import Document
from pinecone import Pinecone

from app.config import settings


class PineconeRetriever:
    """Semantic retriever backed by Pinecone."""

    def __init__(self, index_name: str = settings.pinecone_index_name) -> None:
        self._client = Pinecone(api_key=settings.pinecone_api_key)
        self._index = self._client.Index(index_name)

    def retrieve(self, query: str, k: int = 6) -> list[Document]:
        """Return top-k semantically similar documents for *query*."""
        raise NotImplementedError

    def add_documents(self, documents: list[Document]) -> None:
        """Embed and upsert *documents* into Pinecone."""
        raise NotImplementedError

    def delete_documents(self, ids: list[str]) -> None:
        """Remove documents by ID from the index."""
        raise NotImplementedError

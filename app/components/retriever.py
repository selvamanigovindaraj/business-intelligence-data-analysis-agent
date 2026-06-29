from __future__ import annotations

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone
from pydantic import SecretStr

from app.config import settings


class PineconeRetriever:
    """Semantic retriever backed by Pinecone."""

    def __init__(self, index_name: str = settings.pinecone_index_name) -> None:
        self._client = Pinecone(api_key=settings.pinecone_api_key)
        self._index = self._client.Index(index_name)
        self._embeddings = OpenAIEmbeddings(
            model=settings.embed_model,
            base_url=settings.embed_base_url,
            api_key=SecretStr(settings.embed_api_key),
        )

    def retrieve(self, query: str, k: int = 6) -> list[Document]:
        """Return top-k semantically similar documents for *query*."""
        vector = self._embeddings.embed_query(query)
        result = self._index.query(vector=vector, top_k=k, include_metadata=True)
        return [
            Document(
                page_content=(match.metadata or {}).get("text", ""),
                metadata={key: val for key, val in (match.metadata or {}).items() if key != "text"},
            )
            for match in result.matches
        ]

    def add_documents(self, documents: list[Document]) -> None:
        """Embed and upsert *documents* into Pinecone."""
        texts = [doc.page_content for doc in documents]
        vectors = self._embeddings.embed_documents(texts)
        records = [
            {
                "id": str(i),
                "values": vec,
                "metadata": {"text": doc.page_content, **doc.metadata},
            }
            for i, (doc, vec) in enumerate(zip(documents, vectors, strict=True))
        ]
        self._index.upsert(vectors=records)

    def delete_documents(self, ids: list[str]) -> None:
        """Remove documents by ID from the index."""
        self._index.delete(ids=ids)

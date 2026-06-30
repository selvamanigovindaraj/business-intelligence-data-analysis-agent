from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.tools import BaseTool
from pydantic import PrivateAttr

from app.components.retriever import QdrantRetriever


class VectorSearchTool(BaseTool):
    """Search the internal knowledge base via Qdrant semantic search."""

    name: str = "vector_search"
    description: str = "Search the internal knowledge base via Qdrant semantic search."

    _retriever: QdrantRetriever = PrivateAttr()

    def model_post_init(self, __context: object) -> None:
        self._retriever = QdrantRetriever()

    def _run(self, query: str, k: int = 6) -> list[Document]:
        raise NotImplementedError

    async def _arun(self, query: str, k: int = 6) -> list[Document]:
        raise NotImplementedError

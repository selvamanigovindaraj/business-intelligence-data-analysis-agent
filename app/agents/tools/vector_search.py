from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.tools import BaseTool
from pydantic import PrivateAttr

from app.components.retriever import PineconeRetriever


class VectorSearchTool(BaseTool):
    """Search the internal knowledge base via Pinecone semantic search."""

    name: str = "vector_search"
    description: str = "Search the internal knowledge base via Pinecone semantic search."

    _retriever: PineconeRetriever = PrivateAttr()

    def model_post_init(self, __context: object) -> None:
        self._retriever = PineconeRetriever()

    def _run(self, query: str, k: int = 6) -> list[Document]:
        raise NotImplementedError

    async def _arun(self, query: str, k: int = 6) -> list[Document]:
        raise NotImplementedError

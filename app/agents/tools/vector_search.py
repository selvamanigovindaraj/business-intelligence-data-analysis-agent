from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.tools import tool

from app.components.retriever import PineconeRetriever

_retriever = PineconeRetriever()


@tool
def vector_search(query: str, k: int = 6) -> list[Document]:
    """Search the internal knowledge base via Pinecone semantic search."""
    raise NotImplementedError

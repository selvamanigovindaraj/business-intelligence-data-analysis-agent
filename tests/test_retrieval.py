from __future__ import annotations

from unittest.mock import AsyncMock, patch

from langchain_core.documents import Document

from app.components.retriever import QdrantRetriever


async def test_retrieve_returns_documents() -> None:
    with (
        patch("app.components.retriever.AsyncQdrantClient"),
        patch("app.components.retriever.OpenAIEmbeddings"),
        patch("app.components.retriever.QdrantVectorStore") as mock_vs_cls,
    ):
        mock_store = AsyncMock()
        mock_vs_cls.return_value = mock_store
        mock_store.asimilarity_search.return_value = [Document(page_content="hello world")]

        retriever = QdrantRetriever()
        docs = await retriever.retrieve("test query", k=1)

        assert len(docs) == 1
        assert isinstance(docs[0], Document)
        assert docs[0].page_content == "hello world"
        mock_store.asimilarity_search.assert_called_once_with("test query", k=1)


async def test_add_documents_upserts() -> None:
    with (
        patch("app.components.retriever.AsyncQdrantClient"),
        patch("app.components.retriever.OpenAIEmbeddings"),
        patch("app.components.retriever.QdrantVectorStore") as mock_vs_cls,
    ):
        mock_store = AsyncMock()
        mock_vs_cls.return_value = mock_store

        doc = Document(page_content="hello", metadata={"source": "test"})
        retriever = QdrantRetriever()
        await retriever.add_documents([doc])

        mock_store.aadd_documents.assert_called_once_with([doc])

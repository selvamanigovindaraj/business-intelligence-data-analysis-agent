from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.documents import Document

from app.components.retriever import QdrantRetriever


async def test_retrieve_returns_documents() -> None:
    with (
        patch("app.components.retriever.QdrantClient"),
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
        patch("app.components.retriever.QdrantClient"),
        patch("app.components.retriever.OpenAIEmbeddings"),
        patch("app.components.retriever.QdrantVectorStore") as mock_vs_cls,
    ):
        mock_store = AsyncMock()
        mock_vs_cls.return_value = mock_store
        mock_store.aadd_documents.return_value = ["some-uuid"]

        doc = Document(page_content="hello", metadata={"source": "test"})
        retriever = QdrantRetriever()
        await retriever.add_documents([doc])

        mock_store.aadd_documents.assert_called_once()
        passed_docs: list[Document] = mock_store.aadd_documents.call_args.args[0]
        assert passed_docs[0].page_content == "hello"
        assert passed_docs[0].metadata["source"] == "test"


async def test_ensure_collection_creates_when_missing() -> None:
    with (
        patch("app.components.retriever.QdrantClient") as mock_qdrant_cls,
        patch("app.components.retriever.OpenAIEmbeddings"),
        patch("app.components.retriever.QdrantVectorStore"),
        patch("app.components.retriever.asyncio.to_thread") as mock_thread,
    ):
        mock_client = MagicMock()
        mock_qdrant_cls.return_value = mock_client
        mock_thread.side_effect = [False, None]  # collection_exists=False, create_collection=None

        retriever = QdrantRetriever()
        await retriever.ensure_collection()

        assert mock_thread.call_count == 2
        first_call = mock_thread.call_args_list[0]
        assert first_call.args[0] == mock_client.collection_exists

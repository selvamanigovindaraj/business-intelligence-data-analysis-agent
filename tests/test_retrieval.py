from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.documents import Document

from app.components.retriever import QdrantRetriever


async def test_retrieve_returns_documents() -> None:
    with (
        patch("app.components.retriever.AsyncQdrantClient") as mock_qdrant,
        patch("app.components.retriever.OpenAIEmbeddings") as mock_emb,
    ):
        mock_client = AsyncMock()
        mock_qdrant.return_value = mock_client
        mock_emb.return_value.aembed_query = AsyncMock(return_value=[0.1] * 1536)
        mock_response = MagicMock()
        mock_response.points = [MagicMock(id="1", score=0.9, payload={"text": "hello world"})]
        mock_client.query_points.return_value = mock_response

        retriever = QdrantRetriever()
        docs = await retriever.retrieve("test query", k=1)

        assert len(docs) == 1
        assert isinstance(docs[0], Document)
        assert docs[0].page_content == "hello world"
        mock_client.query_points.assert_called_once()


async def test_add_documents_upserts() -> None:
    with (
        patch("app.components.retriever.AsyncQdrantClient") as mock_qdrant,
        patch("app.components.retriever.OpenAIEmbeddings") as mock_emb,
    ):
        mock_client = AsyncMock()
        mock_qdrant.return_value = mock_client
        mock_emb.return_value.aembed_documents = AsyncMock(return_value=[[0.1] * 1536])

        retriever = QdrantRetriever()
        await retriever.add_documents([Document(page_content="hello", metadata={"source": "test"})])

        mock_client.upsert.assert_called_once()
        points = mock_client.upsert.call_args.kwargs["points"]
        assert points[0].payload["text"] == "hello"
        assert points[0].payload["source"] == "test"

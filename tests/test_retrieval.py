from __future__ import annotations

from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from app.components.retriever import PineconeRetriever


def test_retrieve_returns_documents() -> None:
    with (
        patch("app.components.retriever.Pinecone") as mock_pc,
        patch("app.components.retriever.OpenAIEmbeddings") as mock_emb,
    ):
        mock_index = MagicMock()
        mock_pc.return_value.Index.return_value = mock_index
        mock_emb.return_value.embed_query.return_value = [0.1] * 1536
        mock_index.query.return_value = MagicMock(
            matches=[MagicMock(id="1", score=0.9, metadata={"text": "hello world"})]
        )

        retriever = PineconeRetriever()
        docs = retriever.retrieve("test query", k=1)

        assert len(docs) == 1
        assert isinstance(docs[0], Document)
        assert docs[0].page_content == "hello world"
        mock_index.query.assert_called_once()


def test_add_documents_upserts() -> None:
    with (
        patch("app.components.retriever.Pinecone") as mock_pc,
        patch("app.components.retriever.OpenAIEmbeddings") as mock_emb,
    ):
        mock_index = MagicMock()
        mock_pc.return_value.Index.return_value = mock_index
        mock_emb.return_value.embed_documents.return_value = [[0.1] * 1536]

        retriever = PineconeRetriever()
        retriever.add_documents([Document(page_content="hello", metadata={"source": "test"})])

        mock_index.upsert.assert_called_once()
        vectors = mock_index.upsert.call_args.kwargs["vectors"]
        assert vectors[0]["metadata"]["text"] == "hello"
        assert vectors[0]["metadata"]["source"] == "test"

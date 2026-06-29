from __future__ import annotations

from langchain_core.documents import Document

from app.models import ConversationRequest, ConversationResponse


async def run_rag(request: ConversationRequest) -> ConversationResponse:
    """Retrieve context from Pinecone then generate a grounded answer."""
    raise NotImplementedError


def build_context_prompt(docs: list[Document], query: str) -> str:
    """Format retrieved docs and query into a prompt string."""
    raise NotImplementedError

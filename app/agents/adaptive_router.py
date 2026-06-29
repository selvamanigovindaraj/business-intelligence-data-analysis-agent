from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import StateGraph

from app.models import ConversationRequest, ConversationResponse, Message, RouteDecision, SourceDocument


class AgentState(TypedDict, total=False):
    session_id: str
    message: str
    history: list[Message]
    route: RouteDecision
    sources: list[SourceDocument]
    response: str


def build_graph() -> Any:  # Any: langgraph compiled graph type is not consistently exported
    """Construct and compile the LangGraph agent graph."""
    raise NotImplementedError


async def run_agent(request: ConversationRequest) -> ConversationResponse:
    """Execute the compiled graph for a single user turn."""
    raise NotImplementedError


def _route(state: AgentState) -> RouteDecision:
    """Classify the query and return a routing decision (Groq llama-3.1-8b-instant call)."""
    raise NotImplementedError

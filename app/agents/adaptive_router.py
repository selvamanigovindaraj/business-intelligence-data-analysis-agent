from __future__ import annotations

from typing import Any, TypedDict

from langchain_groq import ChatGroq
from pydantic import SecretStr

from app.config import settings
from app.models import (
    ConversationRequest,
    ConversationResponse,
    Message,
    RouteDecision,
    SourceDocument,
)
from app.prompts.registry import PromptRegistry


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
    # ponytail: per-call LLM init; move to a Router class when the full graph is wired
    llm = ChatGroq(model=settings.router_model, api_key=SecretStr(settings.groq_api_key))
    registry = PromptRegistry()
    message = state.get("message", "")
    result = llm.invoke([
        {"role": "system", "content": registry.get("router")},
        {"role": "user", "content": message},
    ])
    raw = str(result.content).strip().lower()
    try:
        return RouteDecision(raw)
    except ValueError:
        return RouteDecision.DIRECT

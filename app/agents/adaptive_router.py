from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph

from app.models import ConversationRequest, ConversationResponse, RouteDecision


class AgentState(dict):
    """Typed LangGraph state bag — extend with actual keys."""
    pass


def build_graph() -> Any:
    """Construct and compile the LangGraph agent graph."""
    raise NotImplementedError


async def run_agent(request: ConversationRequest) -> ConversationResponse:
    """Execute the compiled graph for a single user turn."""
    raise NotImplementedError


def _route(state: AgentState) -> RouteDecision:
    """Classify the query and return a routing decision (haiku call)."""
    raise NotImplementedError

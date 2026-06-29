from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.agents.adaptive_router import AgentState, _route
from app.models import RouteDecision


def test_route_returns_valid_decision() -> None:
    with patch("app.agents.adaptive_router.ChatGroq") as mock_groq_cls:
        mock_llm = MagicMock()
        mock_groq_cls.return_value = mock_llm
        mock_llm.invoke.return_value = MagicMock(content="rag")

        state: AgentState = {"session_id": "s1", "message": "What is our Q3 revenue?"}
        decision = _route(state)

        assert decision == RouteDecision.RAG
        mock_llm.invoke.assert_called_once()


def test_route_falls_back_to_direct_on_unknown_response() -> None:
    with patch("app.agents.adaptive_router.ChatGroq") as mock_groq_cls:
        mock_llm = MagicMock()
        mock_groq_cls.return_value = mock_llm
        mock_llm.invoke.return_value = MagicMock(content="unknown_gibberish")

        state: AgentState = {"session_id": "s1", "message": "Hello"}
        decision = _route(state)

        assert decision == RouteDecision.DIRECT

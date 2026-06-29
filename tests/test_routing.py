from __future__ import annotations

import pytest

from app.agents.adaptive_router import _route, AgentState
from app.models import RouteDecision


def test_route_returns_valid_decision() -> None:
    # TODO: mock LLM call, assert _route returns a RouteDecision member
    raise NotImplementedError

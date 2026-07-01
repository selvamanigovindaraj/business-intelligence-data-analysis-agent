from __future__ import annotations

from langchain_core.prompts import PromptTemplate

from app.prompts import templates


class PromptRegistry:
    """Registry of named prompt templates."""

    def __init__(self) -> None:
        self._registry: dict[str, PromptTemplate] = {
            "rag": templates.RAG_SYSTEM,
            "router": templates.ROUTER_SYSTEM,
            "direct": templates.DIRECT_SYSTEM,
            "sql": templates.SQL_SYSTEM,
            "sql_correct": templates.SQL_CORRECT_SYSTEM,
            "sql_explain": templates.SQL_EXPLAIN_SYSTEM,
            "python_agent": templates.PYTHON_AGENT_SYSTEM,
        }

    def get(self, name: str) -> PromptTemplate:
        """Return prompt template by name; raise KeyError if not found."""
        return self._registry[name]

    def register(self, name: str, template: PromptTemplate) -> None:
        """Add or replace a named prompt template."""
        self._registry[name] = template

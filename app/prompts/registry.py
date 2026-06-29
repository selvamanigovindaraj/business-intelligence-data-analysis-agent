from __future__ import annotations

from app.prompts import templates


class PromptRegistry:
    """Registry of named prompt templates."""

    def __init__(self) -> None:
        self._registry: dict[str, str] = {
            "rag": templates.RAG_SYSTEM,
            "router": templates.ROUTER_SYSTEM,
            "direct": templates.DIRECT_SYSTEM,
        }

    def get(self, name: str) -> str:
        """Return prompt template by name; raise KeyError if not found."""
        return self._registry[name]

    def register(self, name: str, template: str) -> None:
        """Add or replace a named prompt template."""
        self._registry[name] = template

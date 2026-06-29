from __future__ import annotations

from app.prompts import templates


_REGISTRY: dict[str, str] = {
    "rag": templates.RAG_SYSTEM,
    "router": templates.ROUTER_SYSTEM,
    "direct": templates.DIRECT_SYSTEM,
}


def get_prompt(name: str) -> str:
    """Return prompt template by name; raise KeyError if not found."""
    return _REGISTRY[name]


def register_prompt(name: str, template: str) -> None:
    """Add or replace a named prompt template."""
    _REGISTRY[name] = template

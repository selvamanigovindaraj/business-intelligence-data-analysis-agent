from __future__ import annotations

from langchain_core.tools import tool
from tavily import TavilyClient

from app.config import settings

_client = TavilyClient(api_key=settings.tavily_api_key)


@tool
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the live web via Tavily and return structured results."""
    raise NotImplementedError

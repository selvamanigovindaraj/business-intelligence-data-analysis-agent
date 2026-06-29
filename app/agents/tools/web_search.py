from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import PrivateAttr
from tavily import TavilyClient

from app.config import settings


class WebSearchTool(BaseTool):
    """Search the live web via Tavily and return structured results."""

    name: str = "web_search"
    description: str = "Search the live web via Tavily and return structured results."

    _client: TavilyClient = PrivateAttr()

    def model_post_init(self, __context: object) -> None:
        self._client = TavilyClient(api_key=settings.tavily_api_key)

    def _run(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        raise NotImplementedError

    async def _arun(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        raise NotImplementedError

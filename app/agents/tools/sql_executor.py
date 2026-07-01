from __future__ import annotations

import time
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import settings

log = structlog.get_logger()


class SqlExecutor:
    """Execute a SELECT SQL query against the Northwind Postgres database and return rows."""

    def __init__(self) -> None:
        # Not a LangChain BaseTool: this is called directly from one graph node only,
        # never dispatched by an LLM, and BaseTool's own callback-based tracing produced
        # an unparented duplicate trace alongside the LangGraph node's own span.
        self._engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)

    async def arun(self, sql: str) -> dict[str, Any]:
        start = time.monotonic()
        try:
            async with self._engine.connect() as conn:
                result = await conn.execute(text(sql))
                keys = list(result.keys())
                rows = [dict(zip(keys, row, strict=True)) for row in result.fetchall()]
            elapsed_ms = int((time.monotonic() - start) * 1000)
            log.info("sql executed", row_count=len(rows), execution_time_ms=elapsed_ms)
            return {
                "success": True,
                "rows": rows,
                "row_count": len(rows),
                "execution_time_ms": elapsed_ms,
                "error": None,
            }
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            log.warning("sql execution failed", error=str(exc))
            return {
                "success": False,
                "rows": [],
                "row_count": 0,
                "execution_time_ms": elapsed_ms,
                "error": str(exc),
            }

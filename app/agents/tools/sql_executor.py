from __future__ import annotations

from typing import Any

import asyncpg
import structlog
from langchain_core.tools import BaseTool

from app.config import settings

log = structlog.get_logger()


class SqlExecutorTool(BaseTool):
    """Execute a SELECT SQL query against the Northwind Postgres database and return rows."""

    name: str = "sql_executor"
    description: str = (
        "Execute a SELECT SQL query against the Northwind Postgres database and return rows."
    )

    def _run(self, sql: str) -> list[dict[str, Any]]:
        raise NotImplementedError("Use _arun for async execution.")

    async def _arun(self, sql: str) -> list[dict[str, Any]]:
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        conn = await asyncpg.connect(dsn=dsn)
        try:
            records = await conn.fetch(sql)
        finally:
            await conn.close()
        rows = [dict(r) for r in records]
        log.info("sql executed", row_count=len(rows))
        return rows

from __future__ import annotations

import contextlib
from unittest.mock import AsyncMock, patch

from app.agents.tools.sql_executor import SqlExecutorTool


async def test_arun_returns_rows() -> None:
    with patch("app.agents.tools.sql_executor.asyncpg") as mock_asyncpg:
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [{"order_id": 1, "customer_id": "ALFKI"}]
        mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

        tool = SqlExecutorTool()
        rows = await tool._arun("SELECT order_id, customer_id FROM orders LIMIT 1")

        assert rows == [{"order_id": 1, "customer_id": "ALFKI"}]
        mock_conn.fetch.assert_awaited_once_with(
            "SELECT order_id, customer_id FROM orders LIMIT 1"
        )
        mock_conn.close.assert_awaited_once()


async def test_arun_closes_connection_on_error() -> None:
    with patch("app.agents.tools.sql_executor.asyncpg") as mock_asyncpg:
        mock_conn = AsyncMock()
        mock_conn.fetch.side_effect = Exception("syntax error")
        mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

        tool = SqlExecutorTool()
        with contextlib.suppress(Exception):
            await tool._arun("BAD SQL")

        mock_conn.close.assert_awaited_once()

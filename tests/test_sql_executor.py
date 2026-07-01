from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.tools.sql_executor import SqlExecutorTool


@pytest.fixture()
def mock_engine():
    engine = MagicMock()
    conn = AsyncMock()
    result = MagicMock()
    result.keys.return_value = ["order_id", "customer_id"]
    result.fetchall.return_value = [(1, "ALFKI")]
    conn.execute = AsyncMock(return_value=result)
    engine.connect.return_value.__aenter__ = AsyncMock(return_value=conn)
    engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)
    engine.dispose = AsyncMock()
    return engine


async def test_arun_returns_success_shape(mock_engine) -> None:
    with patch("app.agents.tools.sql_executor.create_async_engine", return_value=mock_engine):
        tool = SqlExecutorTool()
        out = await tool._arun("SELECT order_id, customer_id FROM orders LIMIT 1")

    assert out["success"] is True
    assert out["rows"] == [{"order_id": 1, "customer_id": "ALFKI"}]
    assert out["row_count"] == 1
    assert isinstance(out["execution_time_ms"], int)
    assert out["error"] is None


async def test_arun_returns_error_shape_on_failure(mock_engine) -> None:
    mock_engine.connect.return_value.__aenter__ = AsyncMock(side_effect=Exception("syntax error"))

    with patch("app.agents.tools.sql_executor.create_async_engine", return_value=mock_engine):
        tool = SqlExecutorTool()
        out = await tool._arun("BAD SQL")

    assert out["success"] is False
    assert out["rows"] == []
    assert out["row_count"] == 0
    assert "syntax error" in out["error"]
    assert isinstance(out["execution_time_ms"], int)

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.tools.python_executor import PythonExecutor
from app.models import PythonExecutionResult


@pytest.fixture()
def mock_sandbox():
    sandbox = AsyncMock()
    sandbox.kill = AsyncMock()
    return sandbox


async def test_arun_returns_success_shape(mock_sandbox) -> None:
    execution = AsyncMock()
    execution.error = None
    execution.logs.stdout = ["mean=42.0\n"]
    execution.text = "42.0"
    mock_sandbox.run_code.return_value = execution

    with patch(
        "app.agents.tools.python_executor.AsyncSandbox.create",
        AsyncMock(return_value=mock_sandbox),
    ):
        executor = PythonExecutor()
        out = await executor.arun("print('mean=42.0'); 42.0")

    assert isinstance(out, PythonExecutionResult)
    assert out.success is True
    assert out.stdout == "mean=42.0\n"
    assert out.result == "42.0"
    assert out.error is None
    mock_sandbox.run_code.assert_awaited_once_with("print('mean=42.0'); 42.0")
    mock_sandbox.kill.assert_awaited_once()


async def test_arun_returns_error_shape_on_failure(mock_sandbox) -> None:
    execution = AsyncMock()
    execution.error.name = "NameError"
    execution.error.value = "name 'df' is not defined"
    execution.logs.stdout = []
    execution.text = None
    mock_sandbox.run_code.return_value = execution

    with patch(
        "app.agents.tools.python_executor.AsyncSandbox.create",
        AsyncMock(return_value=mock_sandbox),
    ):
        executor = PythonExecutor()
        out = await executor.arun("bad code")

    assert out.success is False
    assert out.result is None
    assert "df" in out.error
    mock_sandbox.kill.assert_awaited_once()


async def test_arun_kills_sandbox_even_when_run_code_raises(mock_sandbox) -> None:
    mock_sandbox.run_code.side_effect = RuntimeError("sandbox timeout")

    with patch(
        "app.agents.tools.python_executor.AsyncSandbox.create",
        AsyncMock(return_value=mock_sandbox),
    ):
        executor = PythonExecutor()
        out = await executor.arun("print(1)")

    assert out.success is False
    assert "sandbox timeout" in out.error
    mock_sandbox.kill.assert_awaited_once()


async def test_arun_returns_error_shape_when_sandbox_creation_fails() -> None:
    with patch(
        "app.agents.tools.python_executor.AsyncSandbox.create",
        AsyncMock(side_effect=RuntimeError("quota exceeded")),
    ):
        executor = PythonExecutor()
        out = await executor.arun("print(1)")

    assert out.success is False
    assert out.result is None
    assert "quota exceeded" in out.error

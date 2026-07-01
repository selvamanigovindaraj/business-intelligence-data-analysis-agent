from __future__ import annotations

import structlog
from e2b_code_interpreter import AsyncSandbox

from app.config import settings
from app.models import PythonExecutionResult

log = structlog.get_logger()


class PythonExecutor:
    """Runs pandas analysis code in a fresh E2B sandbox."""

    async def arun(self, code: str) -> PythonExecutionResult:
        try:
            sandbox = await AsyncSandbox.create(api_key=settings.e2b_api_key)
        except Exception as exc:  # noqa: BLE001 - sandbox failures are arbitrary
            log.warning("sandbox creation failed", error=str(exc))
            return PythonExecutionResult(success=False, stdout="", result=None, error=str(exc))

        try:
            execution = await sandbox.run_code(code)
        except Exception as exc:  # noqa: BLE001 - sandbox failures are arbitrary
            log.warning("python execution raised", error=str(exc))
            return PythonExecutionResult(success=False, stdout="", result=None, error=str(exc))
        finally:
            await sandbox.kill()

        stdout = "".join(execution.logs.stdout)
        if execution.error:
            error = f"{execution.error.name}: {execution.error.value}"
            log.warning("python execution failed", error=error)
            return PythonExecutionResult(success=False, stdout=stdout, result=None, error=error)

        return PythonExecutionResult(success=True, stdout=stdout, result=execution.text, error=None)

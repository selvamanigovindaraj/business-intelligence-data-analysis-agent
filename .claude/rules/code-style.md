# Code style

- Python 3.11+, `from __future__ import annotations` at top of every file
- Type hints on all function signatures; no `Any` without a comment explaining why
- Line length: 100 characters (ruff enforces this)
- Use `StrEnum` for string enums, `pydantic.BaseModel` for data contracts
- Async-first: prefer `async def` for I/O-bound functions
- No bare `except:`; always catch specific exceptions
- `structlog` for structured logging — never `print()`
- Import order: stdlib → third-party → `app.*` (ruff `isort` handles this)

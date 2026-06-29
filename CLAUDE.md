# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run locally
uvicorn app.main:app --reload          # backend (run from project root)

# Docker
make build    # rebuild images + start all containers detached
make up       # start without rebuilding
make down     # stop containers
make logs     # follow all container logs

# Quality
make check    # ruff lint → mypy → pytest (runs all three sequentially)
uv run ruff check app tests            # lint only
uv run mypy app                        # type-check only

# Tests
uv run pytest                          # all tests
uv run pytest tests/test_cache.py      # single file
uv run pytest -k "test_cache_miss"     # single test by name
uv run pytest --cov=app               # with coverage

# Seed vector store
python scripts/seed.py
```

## Workflow

**TDD is mandatory.** Write a failing test in `tests/test_<module>.py` before touching production code. The test must exist and fail before any implementation is written.

**Before planning or writing code**, run `/ponytail`. If it identifies a simpler path, take it.

## Architecture

The request lifecycle is:

```text
HTTP POST /api/v1/chat
  → app/security/input_guard.py      # validate + injection check
  → app/services/semantic_cache.py   # Redis cache lookup (skip LLM if hit)
  → app/agents/adaptive_router.py    # LangGraph graph entry point
      → _route() calls Groq (llama-3.1-8b-instant) to classify → RouteDecision enum
      → RAG branch:       app/services/rag_pipeline.py → PineconeRetriever → DeepSeek
      → web_search branch: tools/web_search.py (Tavily) → DeepSeek
      → financial branch: tools/financial_data.py → DeepSeek
      → direct branch:    DeepSeek with no retrieval
  → app/security/output_filter.py    # PII masking
  → app/observability/cost_tracker.py # log tokens + cost as OTel span attrs
  → app/services/conversation.py     # persist turn to Postgres
  → cache write-back
  → return ConversationResponse
```

**LLM providers:**

- **DeepSeek** (`deepseek-chat`) — generation. Uses `langchain-openai` with `base_url=settings.deepseek_base_url`. Default model overridable via `LLM_MODEL` env var.
- **Groq** (`llama-3.1-8b-instant`) — routing only (low-latency classification). Uses `langchain-groq`. Model overridable via `ROUTER_MODEL` env var.
- Never import `openai` or `groq` SDKs directly in agent code — always go through the LangChain wrappers so tracing and swapping are transparent.

**Key design decisions:**

- `AgentState` (in `adaptive_router.py`) is the LangGraph state dict — all inter-node data passes through it.
- `RouteDecision` (in `models.py`) is a `StrEnum`; the router node returns one of its values to control graph branching.
- All I/O functions are `async def`; pure logic functions are sync.
- `app/config.py` exposes a single `settings` singleton (Pydantic `BaseSettings`) — import it directly, never read `os.environ` elsewhere.
- Tracing is wired in `app/main.py` lifespan via `init_tracing()` which sets up OTLP → Phoenix at startup. All subsequent spans are emitted automatically.

**Data stores:**

- Pinecone — vector search only (cloud, no local service). Client initialised lazily in `PineconeRetriever.__init__`.
- Postgres — conversation history. Use SQLAlchemy async session; migrations via Alembic.
- Redis — semantic response cache keyed by query embedding hash; TTL defaults to 3600 s.

## Code style

- `from __future__ import annotations` at the top of every Python file.
- Type hints on all signatures. No bare `Any` without a comment.
- `structlog` for logging — no `print()`.
- `StrEnum` for string enums, `pydantic.BaseModel` for data contracts.
- Import order enforced by ruff: stdlib → third-party → `app.*`.
- **No nested functions.** If a helper is needed inside a function, extract it to module level or into a method on a class.
- **No module-level globals.** Mutable state belongs on a class instance; constants (`ALL_CAPS`) are the only acceptable module-level names.
- **Prefer classes for stateful components.** Any code that holds a connection, client, or configuration belongs in a class (`__init__` sets up state, methods operate on it).

## Testing rules

- Mock all external services (Pinecone, Redis, Postgres, Anthropic) in unit tests — never call real APIs.
- `asyncio_mode = "auto"` is set in `pyproject.toml`; no `@pytest.mark.asyncio` needed.
- Integration tests requiring live infra go in `tests/integration/` (excluded from `make check`).

## Coding principles

- **KISS** — simplest solution that satisfies the current requirement.
- **YAGNI** — no hooks, abstractions, or config points for hypothetical futures.
- **Separation of concerns** — I/O, business logic, and presentation in separate layers. LangGraph nodes should not directly call the DB; they call service functions.
- **Law of Demeter** — don't chain through internals (`a.b.c.do()`); pass what is needed.

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

# Evaluation
make eval                    # full 26-question RAGAS eval
make eval LIMIT=5            # smoke-test: first 5 questions
uv run python scripts/run_eval.py --seed-only   # upload dataset only
uv run python scripts/run_eval.py --eval-only   # skip seed, run eval
```

## Workflow

**TDD is mandatory.** Write a failing test in `tests/test_<module>.py` before touching production code. The test must exist and fail before any implementation is written.

**Before planning or writing code**, run `/ponytail`. If it identifies a simpler path, take it.

## Architecture

### Chat stream (SQL generation)

```text
HTTP POST /api/v1/chat/stream
  → app/routers/chat.py              # parse ChatStreamRequest, pull SqlGraph from app.state
  → app/agents/sql_graph.py          # LangGraph pipeline
      → schema_retriever node:  QdrantRetriever.retrieve(question, k=5) → list[TableSchema]
      → sql_generator node:     DeepSeek via llm.with_structured_output(SqlResult, method="json_mode")
  → SSE stream: {"event": "result", "sql": "...", "explanation": "..."} then {"event": "done"}
```

`SqlGraph` is instantiated once at lifespan startup (`app.state.sql_graph`) and reused across requests.

### General chat (adaptive routing)

```text
HTTP POST /api/v1/chat
  → app/security/input_guard.py      # validate + injection check
  → app/services/semantic_cache.py   # Redis cache lookup (skip LLM if hit)
  → app/agents/adaptive_router.py    # LangGraph graph entry point
      → _route() calls Groq (llama-3.1-8b-instant) to classify → RouteDecision enum
      → RAG branch:       app/services/rag_pipeline.py → QdrantRetriever → DeepSeek
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
- `SqlGraph` uses `llm.with_structured_output(SqlResult, method="json_mode")` — `method="json_mode"` avoids `tool_choice`, which DeepSeek's thinking mode rejects. The `_SQL_SYSTEM` prompt must contain the word "json" or DeepSeek returns a 400 error.
- `QdrantRetriever` wraps `langchain-qdrant`'s `QdrantVectorStore` with a single `QdrantClient`. Uses Nebius/Qwen3-Embedding-8B via `OpenAIEmbeddings(tiktoken_enabled=False, check_embedding_ctx_length=False)`. Always initialise with `validate_collection_config=False`.
- All I/O functions are `async def`; pure logic functions are sync.
- `app/config.py` exposes a single `settings` singleton (Pydantic `BaseSettings`) — import it directly, never read `os.environ` elsewhere.
- Tracing is wired in `app/main.py` lifespan via `init_tracing()` which calls `phoenix.otel.register(auto_instrument=True)` — handles LangChain instrumentation automatically; no manual `LangChainInstrumentor().instrument()` calls needed.

**Data stores:**

- Qdrant — vector search (local Docker service, port 6333). Client initialised in `QdrantRetriever.__init__`. Call `ensure_collection()` before first upsert.
- Postgres — conversation history. Use SQLAlchemy async session; migrations via Alembic.
- Redis — semantic response cache keyed by query embedding hash; TTL defaults to 3600 s.

**Models (`app/models.py`):**

- `TableSchema` — `table: str`, `content: str`, `metadata: dict[str, Any]`; represents a retrieved schema doc.
- `SqlResult` — `sql: str`, `explanation: str`; structured output from the sql_generator node.
- `ChatStreamRequest` — `question: str`; request body for `/api/v1/chat/stream`.

## Evaluation pipeline

### Golden dataset

`evals/golden_v1.json` — 26 questions across 3 difficulty tiers (8 simple / 10 medium / 8 complex) covering the Northwind schema. Each entry has `id`, `difficulty`, `question`, `reference_sql`, `reference_tables`, `reference_answer`.

### How it works

```text
scripts/run_eval.py
  Phase 1 — collect:  SqlGraph._graph.ainvoke() for all questions (async, sequential)
  Phase 2 — dataset:  get_or_create_dataset() uploads to Phoenix (idempotent)
  Phase 3 — experiment: async_run_experiment() runs task + evaluators together
      Code evaluators (deterministic):
          sql_generated       — was any SQL produced?
          answer_complete     — is the answer >10 chars?
          rows_returned       — did the executor return rows?
      RAGAS LLM evaluators (require live LLM + embeddings):
          answer_relevancy    — RAGAS AnswerRelevancy; contexts = [question, answer]
          faithfulness        — RAGAS Faithfulness; contexts = actual SQL result rows
          context_precision   — RAGAS ContextPrecisionWithoutReference; contexts = retrieved schemas
```

Results appear in Arize Phoenix → Experiments UI at `http://localhost:6006`.

### Key implementation notes

- **Pre-collection pattern**: all `SqlGraph` outputs are collected before `async_run_experiment`. The task function is a sync dict lookup. This avoids async nesting issues with Phoenix's experiment runner.
- **`AsyncOpenAI` required** for RAGAS: `abatch_score` calls `agenerate()` internally, which requires an async client. Pass `openai.AsyncOpenAI(base_url=..., api_key=...)` to `llm_factory` and `RagasOpenAIEmbeddings`.
- **`async_run_experiment` needs `client=AsyncClient(...)`** passed explicitly — it does not inherit the sync `Client`.
- **`_RAGAS_MAX_TOKENS = 4096`** — default 1024 truncates faithfulness JSON on long answers.
- **`concurrency=3`** — higher values overwhelm the LLM with concurrent faithfulness calls and trigger `IncompleteOutputException`.
- **Vertexai shim** at top of `run_eval.py`: ragas 0.4 hard-imports `langchain_community.chat_models.vertexai` removed in langchain_community 0.4+; patched via `sys.modules` stubs before any ragas import.
- **`@create_evaluator` closures in `_build_ragas_evaluators()`** unavoidably capture metric instances (`ar`, `fa`, `cp`). All scoring business logic is extracted to module-level `_score_*` functions; the closures are thin 3-line adapters — the minimum needed to satisfy the library.
- **PostgreSQL casting**: Northwind monetary columns (`unit_price`, `freight`, `discount`) are stored as `REAL`. `ROUND()` does not accept `double precision` — always cast: `ROUND(expr::numeric, 2)`. This rule is baked into `_SQL_SYSTEM` in `sql_graph.py`.

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

- Mock all external services (Qdrant, Redis, Postgres) in unit tests — never call real APIs.
- `asyncio_mode = "auto"` is set in `pyproject.toml`; no `@pytest.mark.asyncio` needed.
- Integration tests requiring live infra go in `tests/integration/` (excluded from `make check`).

## Coding principles

- **KISS** — simplest solution that satisfies the current requirement.
- **YAGNI** — no hooks, abstractions, or config points for hypothetical futures.
- **Separation of concerns** — I/O, business logic, and presentation in separate layers. LangGraph nodes should not directly call the DB; they call service functions.
- **Law of Demeter** — don't chain through internals (`a.b.c.do()`); pass what is needed.

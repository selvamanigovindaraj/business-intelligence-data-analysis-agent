# Business Intelligence Data Analysis Agent

A production-ready AI agent for business intelligence and data analysis, built with LangGraph, FastAPI, Pinecone, and Arize Phoenix.

## Stack

| Layer | Technology |
|-------|-----------|
| LLM | Anthropic Claude (Sonnet 4.6 for generation, Haiku 4.5 for routing) |
| Agent framework | LangGraph + LangChain |
| API | FastAPI + uvicorn |
| Vector store | Pinecone (cloud-hosted) |
| Web search | Tavily |
| Relational DB | PostgreSQL 16 |
| Cache | Redis 7 |
| Observability | Arize Phoenix (OTLP → Phoenix UI at :6006) |
| Package manager | uv |
| Frontend | React 19 + Vite + TypeScript + Tailwind CSS |

## Quick start

```bash
cp .env.example .env        # fill in API keys
docker compose up --build   # starts backend, frontend, postgres, redis, phoenix
```

Services after boot:

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| Frontend | http://localhost:5173 |
| Phoenix UI | http://localhost:6006 |
| Postgres | localhost:5432 |
| Redis | localhost:6379 |

## Local development (without Docker)

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Seed the vector store

```bash
# Drop documents into data/raw/ then:
python scripts/seed.py
```

## Tests

```bash
pytest
```

## Import convention

All Python imports use the `app.*` prefix (e.g., `from app.config import settings`). Run uvicorn from the project root so `app` is on `sys.path`.

## Observability

Traces are exported via OTLP gRPC to the Phoenix container on port 4317. Open http://localhost:6006 to browse traces, spans, and LLM evals. Set `PHOENIX_PROJECT_NAME` in `.env` to namespace your project.

## License

MIT

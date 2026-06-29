# BI Data Analysis Agent — Claude context

## Stack
- **Backend**: FastAPI + LangGraph + LangChain, Python 3.11, uv
- **LLM**: Anthropic Claude (Sonnet 4.6 generation / Haiku 4.5 routing)
- **Vector store**: Pinecone (cloud) — no local vector service in docker-compose
- **Databases**: PostgreSQL 16 (`agent_db`) + Redis 7
- **Observability**: Arize Phoenix — OTLP gRPC on :4317, UI on :6006
- **Frontend**: React 19 + Vite + TypeScript + Tailwind CSS

## Running

```bash
cp .env.example .env
docker compose up --build
```

## Import convention

All Python imports use the `app.*` prefix. Run uvicorn from the project root:

```bash
uvicorn app.main:app --reload
```

## Key env vars

See `.env.example` for the full list. Minimum to boot:
- `ANTHROPIC_API_KEY`
- `PINECONE_API_KEY`
- `TAVILY_API_KEY`

## Stubs

Most `app/` files are stubs — they import correctly but `raise NotImplementedError`.
Fill them in starting with `app/components/retriever.py` → `app/services/rag_pipeline.py` → `app/agents/adaptive_router.py`.

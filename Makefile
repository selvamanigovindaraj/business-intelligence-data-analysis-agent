.PHONY: check build up down logs hooks install northwind seed eval

.venv/.installed: pyproject.toml
	uv venv
	uv pip install -e ".[dev]"
	@touch .venv/.installed

install: .venv/.installed

check:
	uv run ruff check app tests
	uv run mypy app
	uv run pytest

build: .env
	docker compose up --build -d

.env:
	cp .env.example .env

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

northwind:
	uv run python scripts/load_northwind.py

seed:
	DATABASE_URL=postgresql+asyncpg://agent:agent_secret@localhost:5432/northwind \
	QDRANT_URL=http://localhost:6333 \
	PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4317 \
	uv run python scripts/seed.py

# Usage: make eval              → full 26-question run
#        make eval LIMIT=5     → smoke-test with first 5 questions
LIMIT ?= 0
eval:
	DATABASE_URL=postgresql+asyncpg://agent:agent_secret@localhost:5432/northwind \
	QDRANT_URL=http://localhost:6333 \
	PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4317 \
	uv run python scripts/run_eval.py $(if $(filter-out 0,$(LIMIT)),--limit $(LIMIT),)

hooks:
	uv run pre-commit install

.PHONY: check build up down logs hooks install

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

hooks: .venv/.installed
	uv run pre-commit install

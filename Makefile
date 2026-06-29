.PHONY: check build up down logs

check:
	uv run ruff check app tests
	uv run mypy app
	uv run pytest

build:
	docker compose up --build -d

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

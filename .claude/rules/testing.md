# Testing

- Use `pytest` + `pytest-asyncio` (asyncio_mode = "auto" in pyproject.toml)
- Mock external services (Pinecone, Redis, Postgres, Anthropic) — never hit real APIs in unit tests
- One test file per module: `tests/test_<module>.py`
- Test names: `test_<function>_<scenario>` (e.g., `test_retrieve_returns_documents`)
- No test frameworks other than pytest; no fixtures files unless shared across 3+ test files
- Integration tests that need real infrastructure go in `tests/integration/` (not run in CI by default)

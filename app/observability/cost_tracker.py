from __future__ import annotations


# Approximate pricing per 1M tokens (USD) — update as Anthropic changes rates
_PRICE_PER_M: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 0.25, "output": 1.25},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return estimated USD cost for a completion call."""
    raise NotImplementedError


def log_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    session_id: str | None = None,
) -> None:
    """Log cost to structured logger and attach as OTel span attribute."""
    raise NotImplementedError

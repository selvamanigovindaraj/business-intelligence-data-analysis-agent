from __future__ import annotations

# Approximate pricing per 1M tokens (USD)
PRICE_PER_M: dict[str, dict[str, float]] = {
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    # Groq-hosted models
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
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

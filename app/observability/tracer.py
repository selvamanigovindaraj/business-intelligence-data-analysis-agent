from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from phoenix.otel import register

from app.config import settings


def init_tracing() -> TracerProvider:
    """Wire up OpenTelemetry → Arize Phoenix."""
    provider = register(
        project_name=settings.phoenix_project_name,
        endpoint=settings.phoenix_collector_endpoint,
        auto_instrument=True,
    )
    return provider  # type: ignore[return-value]


def get_tracer(name: str = __name__) -> trace.Tracer:
    return trace.get_tracer(name)

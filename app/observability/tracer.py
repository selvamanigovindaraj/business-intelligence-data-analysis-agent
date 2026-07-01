from __future__ import annotations

from openinference.instrumentation.openai import OpenAIInstrumentor
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
    # auto_instrument=True also activates OpenAIInstrumentor (pulled in transitively),
    # which double-traces every LangChain LLM call as a second, unparented root span.
    # LangChainInstrumentor already captures these calls correctly nested; drop the redundant one.
    OpenAIInstrumentor().uninstrument()
    return provider


def get_tracer(name: str = __name__) -> trace.Tracer:
    return trace.get_tracer(name)

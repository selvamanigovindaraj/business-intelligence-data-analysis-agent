from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.observability.tracer import init_tracing


def test_init_tracing_uninstruments_redundant_openai_instrumentor() -> None:
    with (
        patch("app.observability.tracer.register") as mock_register,
        patch("app.observability.tracer.OpenAIInstrumentor") as mock_openai_instrumentor_cls,
    ):
        mock_register.return_value = MagicMock()
        mock_instrumentor = MagicMock()
        mock_openai_instrumentor_cls.return_value = mock_instrumentor

        init_tracing()

        mock_instrumentor.uninstrument.assert_called_once()

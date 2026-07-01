from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.documents import Document

from app.agents.sql_graph import (
    SqlGraph,
    _route_after_execution,
    _route_after_explanation,
    _route_after_validation,
)
from app.models import PythonCodeBlock, PythonExecutionResult, SqlResult, TableSchema

# ---------------------------------------------------------------------------
# Routing functions (pure — no mocks needed)
# ---------------------------------------------------------------------------


def test_route_after_validation_no_error_goes_to_executor() -> None:
    assert _route_after_validation({"sql": "SELECT 1"}) == "sql_executor"


def test_route_after_validation_error_under_limit_goes_to_corrector() -> None:
    state = {"validation_error": "bad table", "retry_count": 2}
    assert _route_after_validation(state) == "sql_corrector"


def test_route_after_validation_error_at_limit_goes_to_error_response() -> None:
    state = {"validation_error": "bad table", "retry_count": 3}
    assert _route_after_validation(state) == "error_response"


def test_route_after_execution_success_goes_to_explainer() -> None:
    assert _route_after_execution({"execution_error": None}) == "result_explainer"


def test_route_after_execution_failure_under_limit_goes_to_corrector() -> None:
    state = {"execution_error": "syntax error", "retry_count": 0}
    assert _route_after_execution(state) == "sql_corrector"


def test_route_after_execution_failure_at_limit_goes_to_error_response() -> None:
    state = {"execution_error": "syntax error", "retry_count": 3}
    assert _route_after_execution(state) == "error_response"


def test_route_after_explanation_goes_to_python_agent_when_analyze_requested() -> None:
    assert _route_after_explanation({"analyze": True}) == "python_agent"


def test_route_after_explanation_ends_when_analyze_not_requested() -> None:
    from langgraph.graph import END

    assert _route_after_explanation({"analyze": False}) == END
    assert _route_after_explanation({}) == END


# ---------------------------------------------------------------------------
# Validator node
# ---------------------------------------------------------------------------


async def test_sql_validator_node_passes_valid_sql() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever"),
        patch("app.agents.sql_graph.ChatOpenAI"),
        patch("app.agents.sql_graph.validate_sql", return_value=None),
    ):
        graph = SqlGraph()
        state = {
            "sql": "SELECT * FROM orders",
            "schemas": [TableSchema(table="orders", content="Table: orders", metadata={})],
        }
        result = graph._sql_validator_node(state)
        assert result.get("validation_error") is None


async def test_sql_validator_node_rejects_invalid_sql() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever"),
        patch("app.agents.sql_graph.ChatOpenAI"),
        patch("app.agents.sql_graph.validate_sql", return_value="Unknown table(s): bogus"),
    ):
        graph = SqlGraph()
        state = {
            "sql": "SELECT * FROM bogus",
            "schemas": [TableSchema(table="orders", content="Table: orders", metadata={})],
        }
        result = graph._sql_validator_node(state)
        assert result["validation_error"] == "Unknown table(s): bogus"


# ---------------------------------------------------------------------------
# Corrector node
# ---------------------------------------------------------------------------


async def test_sql_corrector_node_generates_corrected_sql() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever"),
        patch("app.agents.sql_graph.SqlExecutor"),
        patch("app.agents.sql_graph.ChatOpenAI") as mock_llm_cls,
    ):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_chain = AsyncMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke.return_value = SqlResult(
            sql="SELECT order_id FROM orders",
            explanation="Removed invalid column bad_col.",
        )

        graph = SqlGraph()
        state = {
            "sql": "SELECT bad_col FROM orders",
            "validation_error": "Unknown column(s): bad_col",
            "execution_error": None,
            "schemas": [TableSchema(table="orders", content="Table: orders", metadata={})],
            "retry_count": 0,
            "error_history": [],
        }
        result = await graph._sql_corrector_node(state)

        assert result["sql"] == "SELECT order_id FROM orders"
        assert result["retry_count"] == 1
        assert len(result["error_history"]) == 1
        assert result["error_history"][0]["sql"] == "SELECT bad_col FROM orders"
        assert result["error_history"][0]["attempt"] == 1
        assert result["validation_error"] is None
        assert result["execution_error"] is None


async def test_sql_corrector_node_accumulates_error_history() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever"),
        patch("app.agents.sql_graph.SqlExecutor"),
        patch("app.agents.sql_graph.ChatOpenAI") as mock_llm_cls,
    ):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_chain = AsyncMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke.return_value = SqlResult(sql="SELECT 1", explanation="Fixed.")

        graph = SqlGraph()
        state = {
            "sql": "STILL BAD",
            "validation_error": "Unknown table(s): foo",
            "execution_error": None,
            "schemas": [],
            "retry_count": 1,
            "error_history": [{"sql": "FIRST BAD", "error": "prior error", "attempt": 1}],
        }
        result = await graph._sql_corrector_node(state)

        assert result["retry_count"] == 2
        # the node itself returns only the new entry; LangGraph's operator.add reducer
        # merges it with existing state on the graph's own state update, not here
        assert len(result["error_history"]) == 1
        assert result["error_history"][0]["attempt"] == 2


async def test_sql_corrector_node_attaches_retry_count_to_trace_metadata() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever"),
        patch("app.agents.sql_graph.SqlExecutor"),
        patch("app.agents.sql_graph.ChatOpenAI") as mock_llm_cls,
    ):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_chain = AsyncMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke.return_value = SqlResult(sql="SELECT 1", explanation="Fixed.")

        graph = SqlGraph()
        state = {
            "sql": "STILL BAD",
            "validation_error": "Unknown table(s): foo",
            "execution_error": None,
            "schemas": [],
            "retry_count": 1,
            "error_history": [],
        }
        await graph._sql_corrector_node(state)

        _, kwargs = mock_chain.ainvoke.call_args
        assert kwargs["config"]["metadata"]["retry_count"] == 2


# ---------------------------------------------------------------------------
# Error response node
# ---------------------------------------------------------------------------


async def test_error_response_node_returns_graceful_message() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever"),
        patch("app.agents.sql_graph.ChatOpenAI"),
        patch("app.agents.sql_graph.SqlExecutor"),
    ):
        graph = SqlGraph()
        state = {
            "validation_error": "hopeless",
            "execution_error": None,
            "sql": "GIVING UP",
            "retry_count": 3,
        }
        result = await graph._error_response_node(state)

        assert "answer" in result
        assert len(result["answer"]) > 10
        assert "3 attempt" in result["answer"]


# ---------------------------------------------------------------------------
# Schema retriever node
# ---------------------------------------------------------------------------


async def test_schema_retriever_node_returns_schemas() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever") as mock_retriever_cls,
        patch("app.agents.sql_graph.ChatOpenAI"),
    ):
        mock_retriever = AsyncMock()
        mock_retriever_cls.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            Document(
                page_content="Table: orders\nStores order records.",
                metadata={"table": "orders", "type": "table"},
            )
        ]

        graph = SqlGraph()
        result = await graph._schema_retriever_node({"question": "list all orders"})

        assert "schemas" in result
        schemas: list[TableSchema] = result["schemas"]  # type: ignore[assignment]
        assert len(schemas) == 1
        assert schemas[0].table == "orders"
        assert "orders" in schemas[0].content
        mock_retriever.retrieve.assert_awaited_once_with("list all orders", k=5)


# ---------------------------------------------------------------------------
# Generator node
# ---------------------------------------------------------------------------


async def test_sql_generator_node_returns_sql() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever"),
        patch("app.agents.sql_graph.ChatOpenAI") as mock_llm_cls,
    ):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_chain = AsyncMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke.return_value = SqlResult(
            sql="SELECT * FROM orders", explanation="Fetches all orders."
        )

        graph = SqlGraph()
        state = {
            "question": "list all orders",
            "schemas": [
                TableSchema(
                    table="orders",
                    content="Table: orders\nStores order records.",
                    metadata={},
                )
            ],
        }
        result = await graph._sql_generator_node(state)

        assert result["sql"] == "SELECT * FROM orders"
        assert result["explanation"] == "Fetches all orders."
        mock_llm.with_structured_output.assert_any_call(SqlResult, method="json_mode")


# ---------------------------------------------------------------------------
# Executor node
# ---------------------------------------------------------------------------


async def test_sql_executor_node_returns_rows_and_execution_error() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever"),
        patch("app.agents.sql_graph.ChatOpenAI"),
        patch("app.agents.sql_graph.SqlExecutor") as mock_tool_cls,
    ):
        mock_tool = AsyncMock()
        mock_tool_cls.return_value = mock_tool
        mock_tool.arun.return_value = {
            "success": True,
            "rows": [{"id": 1, "company_name": "Acme"}],
            "row_count": 1,
            "execution_time_ms": 5,
            "error": None,
        }

        graph = SqlGraph()
        result = await graph._sql_executor_node({"sql": "SELECT * FROM customers LIMIT 1"})

        assert result["rows"] == [{"id": 1, "company_name": "Acme"}]
        assert result["execution_error"] is None
        mock_tool.arun.assert_awaited_once_with("SELECT * FROM customers LIMIT 1")


# ---------------------------------------------------------------------------
# Result explainer node
# ---------------------------------------------------------------------------


async def test_result_explainer_node_returns_answer() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever"),
        patch("app.agents.sql_graph.ChatOpenAI") as mock_llm_cls,
    ):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.with_structured_output.return_value = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "There is 1 customer: Acme."
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        graph = SqlGraph()
        state = {
            "question": "How many customers?",
            "sql": "SELECT count(*) FROM customers",
            "rows": [{"count": 1}],
        }
        result = await graph._result_explainer_node(state)

        assert result["answer"] == "There is 1 customer: Acme."
        mock_llm.ainvoke.assert_awaited_once()


# ---------------------------------------------------------------------------
# Python agent / executor nodes
# ---------------------------------------------------------------------------


async def test_python_agent_node_returns_code() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever"),
        patch("app.agents.sql_graph.ChatOpenAI") as mock_llm_cls,
    ):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_chain = AsyncMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke.return_value = PythonCodeBlock(
            code="result = df['unit_price'].mean()",
            expected_output_description="Average unit price.",
        )

        graph = SqlGraph()
        state = {
            "question": "What is the average unit price?",
            "rows": [{"unit_price": 10.0}, {"unit_price": 20.0}],
        }
        result = await graph._python_agent_node(state)

        assert result["python_code"] == "result = df['unit_price'].mean()"
        mock_llm.with_structured_output.assert_any_call(PythonCodeBlock, method="json_mode")


async def test_python_executor_node_returns_analysis_fields() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever"),
        patch("app.agents.sql_graph.ChatOpenAI"),
        patch("app.agents.sql_graph.PythonExecutor") as mock_tool_cls,
    ):
        mock_tool = AsyncMock()
        mock_tool_cls.return_value = mock_tool
        mock_tool.arun.return_value = PythonExecutionResult(
            success=True, stdout="", result="15.0", error=None
        )

        graph = SqlGraph()
        state = {
            "rows": [{"unit_price": 10.0}, {"unit_price": 20.0}],
            "python_code": "result = df['unit_price'].mean()",
        }
        result = await graph._python_executor_node(state)

        assert result["analysis_success"] is True
        assert result["analysis_result"] == "15.0"
        assert result["analysis_error"] is None
        mock_tool.arun.assert_awaited_once()
        executed_script = mock_tool.arun.call_args.args[0]
        assert "df = pd.DataFrame" in executed_script
        assert "result = df['unit_price'].mean()" in executed_script
        assert executed_script.rstrip().endswith("result")


# ---------------------------------------------------------------------------
# Stream integration
# ---------------------------------------------------------------------------


async def test_stream_emits_result_then_done() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever") as mock_retriever_cls,
        patch("app.agents.sql_graph.ChatOpenAI") as mock_llm_cls,
        patch("app.agents.sql_graph.SqlExecutor") as mock_tool_cls,
    ):
        mock_retriever = AsyncMock()
        mock_retriever_cls.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            Document(
                page_content="Table: products\nStores product catalog.",
                metadata={"table": "products", "type": "table"},
            )
        ]

        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_chain = AsyncMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke.return_value = SqlResult(
            sql="SELECT * FROM products", explanation="Lists all products."
        )
        mock_response = MagicMock()
        mock_response.content = "There are 5 products in the catalog."
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_tool = AsyncMock()
        mock_tool_cls.return_value = mock_tool
        mock_tool.arun.return_value = {
            "success": True,
            "rows": [{"product_id": 1, "product_name": "Chai"}],
            "row_count": 1,
            "execution_time_ms": 3,
            "error": None,
        }

        graph = SqlGraph()
        events: list[dict[str, object]] = []
        async for raw in graph.stream("show all products"):
            line = raw.strip()
            if line.startswith("data: "):
                events.append(json.loads(line.removeprefix("data: ")))

        assert len(events) == 2  # result, done
        assert events[0]["event"] == "result"
        assert events[0]["sql"] == "SELECT * FROM products"
        assert events[0]["explanation"] == "Lists all products."
        assert events[0]["answer"] == "There are 5 products in the catalog."
        assert events[0]["rows"] == [{"product_id": 1, "product_name": "Chai"}]
        assert events[1]["event"] == "done"


async def test_stream_emits_analysis_event_when_analyze_requested() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever") as mock_retriever_cls,
        patch("app.agents.sql_graph.ChatOpenAI") as mock_llm_cls,
        patch("app.agents.sql_graph.SqlExecutor") as mock_tool_cls,
        patch("app.agents.sql_graph.PythonExecutor") as mock_py_tool_cls,
    ):
        mock_retriever = AsyncMock()
        mock_retriever_cls.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            Document(
                page_content="Table: products\nStores product catalog.",
                metadata={"table": "products", "type": "table"},
            )
        ]

        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_sql_chain = AsyncMock()
        mock_py_chain = AsyncMock()

        def structured_output(model, method):
            return mock_py_chain if model is PythonCodeBlock else mock_sql_chain

        mock_llm.with_structured_output.side_effect = structured_output
        mock_sql_chain.ainvoke.return_value = SqlResult(
            sql="SELECT * FROM products", explanation="Lists all products."
        )
        mock_py_chain.ainvoke.return_value = PythonCodeBlock(
            code="result = len(df)", expected_output_description="Row count."
        )
        mock_response = MagicMock()
        mock_response.content = "There are 5 products in the catalog."
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        mock_tool = AsyncMock()
        mock_tool_cls.return_value = mock_tool
        mock_tool.arun.return_value = {
            "success": True,
            "rows": [{"product_id": 1, "product_name": "Chai"}],
            "row_count": 1,
            "execution_time_ms": 3,
            "error": None,
        }

        mock_py_tool = AsyncMock()
        mock_py_tool_cls.return_value = mock_py_tool
        mock_py_tool.arun.return_value = PythonExecutionResult(
            success=True, stdout="", result="1", error=None
        )

        graph = SqlGraph()
        events: list[dict[str, object]] = []
        async for raw in graph.stream("show all products", analyze=True):
            line = raw.strip()
            if line.startswith("data: "):
                events.append(json.loads(line.removeprefix("data: ")))

        assert len(events) == 3  # result, analysis, done
        assert events[1]["event"] == "analysis"
        assert events[1]["success"] is True
        assert events[1]["result"] == "1"
        assert events[2]["event"] == "done"


async def test_stream_emits_error_event_after_max_retries() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever") as mock_retriever_cls,
        patch("app.agents.sql_graph.ChatOpenAI") as mock_llm_cls,
        patch("app.agents.sql_graph.SqlExecutor"),
        patch("app.agents.sql_graph.validate_sql", return_value="Unknown table(s): bogus"),
    ):
        mock_retriever = AsyncMock()
        mock_retriever_cls.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            Document(
                page_content="Table: orders\nStores orders.",
                metadata={"table": "orders", "type": "table"},
            )
        ]
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_chain = AsyncMock()
        mock_llm.with_structured_output.return_value = mock_chain
        # Both generator and corrector use the same chain mock
        mock_chain.ainvoke.return_value = SqlResult(
            sql="SELECT * FROM bogus", explanation="Attempted fix."
        )

        graph = SqlGraph()
        events: list[dict[str, object]] = []
        async for raw in graph.stream("show bogus data"):
            line = raw.strip()
            if line.startswith("data: "):
                events.append(json.loads(line.removeprefix("data: ")))

        assert any(e["event"] == "error" for e in events)
        assert not any(e["event"] == "result" for e in events)
        error_event = next(e for e in events if e["event"] == "error")
        assert "message" in error_event

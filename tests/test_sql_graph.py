from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.documents import Document

from app.agents.sql_graph import SqlGraph
from app.models import SqlResult, TableSchema


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
        mock_llm.with_structured_output.assert_called_once_with(SqlResult, method="json_mode")


async def test_sql_executor_node_returns_rows() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever"),
        patch("app.agents.sql_graph.ChatOpenAI"),
        patch("app.agents.sql_graph.SqlExecutorTool") as mock_tool_cls,
    ):
        mock_tool = AsyncMock()
        mock_tool_cls.return_value = mock_tool
        mock_tool._arun.return_value = {
            "success": True,
            "rows": [{"id": 1, "company_name": "Acme"}],
            "row_count": 1,
            "execution_time_ms": 5,
            "error": None,
        }

        graph = SqlGraph()
        result = await graph._sql_executor_node({"sql": "SELECT * FROM customers LIMIT 1"})

        assert result["rows"] == [{"id": 1, "company_name": "Acme"}]
        mock_tool._arun.assert_awaited_once_with("SELECT * FROM customers LIMIT 1")


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


async def test_stream_emits_result_then_done() -> None:
    with (
        patch("app.agents.sql_graph.QdrantRetriever") as mock_retriever_cls,
        patch("app.agents.sql_graph.ChatOpenAI") as mock_llm_cls,
        patch("app.agents.sql_graph.SqlExecutorTool") as mock_tool_cls,
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
        mock_tool._arun.return_value = {
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
        assert events[0]["answer"] == "There are 5 products in the catalog."
        assert events[0]["rows"] == [{"product_id": 1, "product_name": "Chai"}]
        assert events[1]["event"] == "done"

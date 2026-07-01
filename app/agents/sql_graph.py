from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any, TypedDict

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import SecretStr

from app.agents.tools.sql_executor import SqlExecutorTool
from app.agents.tools.sql_validator import validate_sql
from app.components.retriever import QdrantRetriever
from app.config import settings
from app.models import SqlResult, TableSchema

log = structlog.get_logger()

_SQL_SYSTEM = """\
You are a SQL expert for a PostgreSQL Northwind trading company database.
Use only the table schemas provided to write your query.
Return JSON with "sql" (a single SELECT statement) and "explanation" (one sentence).

PostgreSQL rules you must follow:
- Monetary columns (unit_price, freight) and discount are stored as REAL (double precision).
  ROUND() does not accept double precision — always cast first: ROUND(expr::numeric, 2).
- Use EXTRACT(YEAR FROM col) and EXTRACT(MONTH FROM col) for date parts.
- Use DATE_TRUNC('month', col) for monthly grouping.
- Prefer NULLIF(denominator, 0) when dividing to avoid division-by-zero.
"""

_EXPLAIN_SYSTEM = (
    "You are a data analyst. Given the question, SQL query, and its results, "
    "provide a clear and concise answer in plain English."
)


class SqlState(TypedDict, total=False):
    question: str
    schemas: list[TableSchema]
    sql: str
    explanation: str
    validation_error: str | None
    rows: list[dict[str, Any]]
    answer: str


class SqlGraph:
    """LangGraph pipeline: schema_retriever → sql_generator → sql_executor → result_explainer."""

    def __init__(self) -> None:
        self._retriever = QdrantRetriever()
        self._executor = SqlExecutorTool()
        self._llm = ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.deepseek_base_url,
            api_key=SecretStr(settings.deepseek_api_key),
            temperature=0,
        )
        # method="json_mode" avoids tool_choice, which is incompatible with DeepSeek thinking mode
        self._sql_chain = self._llm.with_structured_output(SqlResult, method="json_mode")
        self._graph: Any = self._build()

    def _build(self) -> Any:  # Any: CompiledStateGraph not consistently exported
        graph: StateGraph[SqlState] = StateGraph(SqlState)
        graph.add_node("schema_retriever", self._schema_retriever_node)
        graph.add_node("sql_generator", self._sql_generator_node)
        graph.add_node("sql_validator", self._sql_validator_node)
        graph.add_node("sql_executor", self._sql_executor_node)
        graph.add_node("result_explainer", self._result_explainer_node)
        graph.set_entry_point("schema_retriever")
        graph.add_edge("schema_retriever", "sql_generator")
        graph.add_edge("sql_generator", "sql_validator")
        graph.add_conditional_edges(
            "sql_validator",
            lambda state: END if state.get("validation_error") else "sql_executor",
        )
        graph.add_edge("sql_executor", "result_explainer")
        graph.set_finish_point("result_explainer")
        return graph.compile()

    async def _schema_retriever_node(self, state: SqlState) -> SqlState:
        question = state["question"]
        docs = await self._retriever.retrieve(question, k=5)
        log.info("schemas retrieved", question=question, count=len(docs))
        schemas = [
            TableSchema(
                table=doc.metadata.get("table", ""),
                content=doc.page_content,
                metadata=doc.metadata,
            )
            for doc in docs
        ]
        return {"schemas": schemas}

    async def _sql_generator_node(self, state: SqlState) -> SqlState:
        schemas = state["schemas"]
        schema_text = "\n\n".join(s.content for s in schemas)
        system = f"{_SQL_SYSTEM}\nRelevant schemas:\n{schema_text}"
        result: SqlResult = await self._sql_chain.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=state["question"]),
        ])
        log.info("sql generated", table_count=len(schemas))
        return {"sql": result.sql, "explanation": result.explanation}

    async def _sql_validator_node(self, state: SqlState) -> SqlState:
        error = validate_sql(state["sql"], state.get("schemas", []))
        if error:
            log.warning("sql validation failed", error=error)
        return {"validation_error": error}

    async def _sql_executor_node(self, state: SqlState) -> SqlState:
        result = await self._executor._arun(state["sql"])
        return {"rows": result["rows"]}

    async def _result_explainer_node(self, state: SqlState) -> SqlState:
        rows_text = json.dumps(state["rows"][:50], default=str)
        human = f"Question: {state['question']}\nSQL: {state['sql']}\nResults:\n{rows_text}"
        response = await self._llm.ainvoke([
            SystemMessage(content=_EXPLAIN_SYSTEM),
            HumanMessage(content=human),
        ])
        answer: str = response.content  # type: ignore[assignment]
        log.info("result explained", answer_len=len(answer))
        return {"answer": answer}

    async def stream(self, question: str) -> AsyncGenerator[str, None]:
        sql = ""
        rows: list[dict[str, Any]] = []
        async for chunk in self._graph.astream(
            {"question": question}, stream_mode="updates"
        ):
            if "sql_generator" in chunk:
                sql = chunk["sql_generator"].get("sql", "")
            if "sql_validator" in chunk:
                error = chunk["sql_validator"].get("validation_error")
                if error:
                    yield f"data: {json.dumps({'event': 'validation_error', 'message': error})}\n\n"
            if "sql_executor" in chunk:
                rows = chunk["sql_executor"].get("rows", [])
            if "result_explainer" in chunk:
                node_out = chunk["result_explainer"]
                payload = {
                    "event": "result",
                    "sql": sql,
                    "rows": rows,
                    "answer": node_out.get("answer", ""),
                }
                yield f"data: {json.dumps(payload, default=str)}\n\n"
        yield 'data: {"event": "done"}\n\n'

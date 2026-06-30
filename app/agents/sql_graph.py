from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any, TypedDict

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from pydantic import SecretStr

from app.components.retriever import QdrantRetriever
from app.config import settings
from app.models import SqlResult, TableSchema

log = structlog.get_logger()

_SQL_SYSTEM = """\
You are a SQL expert for a PostgreSQL Northwind trading company database.
Use only the table schemas provided to write your query.
Return JSON with "sql" (a single SELECT statement) and "explanation" (one sentence).
"""


class SqlState(TypedDict, total=False):
    question: str
    schemas: list[TableSchema]
    sql: str
    explanation: str


class SqlGraph:
    """LangGraph pipeline: schema_retriever → sql_generator."""

    def __init__(self) -> None:
        self._retriever = QdrantRetriever()
        llm = ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.deepseek_base_url,
            api_key=SecretStr(settings.deepseek_api_key),
            temperature=0,
        )
        # method="json_mode" avoids tool_choice, which is incompatible with DeepSeek thinking mode
        self._sql_chain = llm.with_structured_output(SqlResult, method="json_mode")
        self._graph: Any = self._build()

    def _build(self) -> Any:  # Any: CompiledStateGraph not consistently exported
        graph: StateGraph[SqlState] = StateGraph(SqlState)
        graph.add_node("schema_retriever", self._schema_retriever_node)
        graph.add_node("sql_generator", self._sql_generator_node)
        graph.set_entry_point("schema_retriever")
        graph.add_edge("schema_retriever", "sql_generator")
        graph.set_finish_point("sql_generator")
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

    async def stream(self, question: str) -> AsyncGenerator[str, None]:
        async for chunk in self._graph.astream(
            {"question": question}, stream_mode="updates"
        ):
            if "sql_generator" in chunk:
                node_out = chunk["sql_generator"]
                payload = {
                    "event": "result",
                    "sql": node_out.get("sql", ""),
                    "explanation": node_out.get("explanation", ""),
                }
                yield f"data: {json.dumps(payload)}\n\n"
        yield 'data: {"event": "done"}\n\n'

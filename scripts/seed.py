"""Seed Qdrant with Northwind schema metadata.

For every table and column in the northwind DB, an LLM generates a
natural-language description and tags; those are embedded and stored in the
Qdrant northwind collection for semantic retrieval.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

import asyncpg
import structlog
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from opentelemetry import trace
from pydantic import BaseModel, SecretStr
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.components.retriever import QdrantRetriever
from app.config import settings
from app.observability.tracer import init_tracing

log = structlog.get_logger()

_SYSTEM_PROMPT = (
    "You are a database documentation expert for a Northwind trading company database. "
    "Always respond with valid JSON only — no markdown fences, no extra text."
)

_TABLE_PROMPT = """\
Table: {table}
Columns:
{columns}

Return a JSON object with exactly this shape:
{{
  "table_description": "<one sentence describing what this table stores>",
  "columns": {{
    "<column_name>": "<one sentence describing what this column stores>"
  }}
}}
"""


@dataclass
class _ColumnInfo:
    name: str
    data_type: str


class _TableDescriptions(BaseModel):
    table_description: str
    columns: dict[str, str]


async def _introspect(conn_url: str) -> dict[str, list[_ColumnInfo]]:
    conn: asyncpg.Connection = await asyncpg.connect(conn_url)
    try:
        rows = await conn.fetch(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
            """
        )
    finally:
        await conn.close()

    schema: dict[str, list[_ColumnInfo]] = {}
    for row in rows:
        schema.setdefault(row["table_name"], []).append(
            _ColumnInfo(row["column_name"], row["data_type"])
        )
    return schema


@retry(
    retry=retry_if_exception_type((json.JSONDecodeError, ValueError)),
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    reraise=True,
)
async def _generate_descriptions(
    table: str, columns: list[_ColumnInfo], llm: ChatOpenAI
) -> _TableDescriptions:
    col_lines = "\n".join(f"  - {c.name} ({c.data_type})" for c in columns)
    prompt = _TABLE_PROMPT.format(table=table, columns=col_lines)
    response = await llm.ainvoke(
        [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=prompt)]
    )
    content = response.content.strip()
    if not content:
        raise ValueError(f"empty response from DeepSeek for table {table}")
    return _TableDescriptions.model_validate_json(content)


def _build_documents(
    table: str, columns: list[_ColumnInfo], descriptions: _TableDescriptions
) -> list[Document]:
    docs: list[Document] = []

    table_desc = descriptions.table_description
    col_descriptions = descriptions.columns

    col_lines = "\n".join(
        f"  - {c.name} ({c.data_type}): {col_descriptions.get(c.name, c.data_type)}"
        for c in columns
    )
    table_chunk = f"Table: {table}\n{table_desc}\n\nColumns:\n{col_lines}"
    docs.append(
        Document(
            page_content=table_chunk,
            metadata={
                "db": "northwind",
                "type": "table",
                "table": table,
                "tags": ["db:northwind", f"table:{table}", "type:table"],
                "columns": [{"name": c.name, "data_type": c.data_type} for c in columns],
            },
        )
    )

    return docs


def _make_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.deepseek_base_url,
        api_key=SecretStr(settings.deepseek_api_key),
        # json_object mode avoids tool_choice (incompatible with DeepSeek thinking mode)
        model_kwargs={"response_format": {"type": "json_object"}},
        temperature=0,
    )


async def _generate_all_documents(
    schema: dict[str, list[_ColumnInfo]], llm: ChatOpenAI
) -> list[Document]:
    all_docs: list[Document] = []
    for table, columns in schema.items():
        log.info("generating descriptions", table=table, columns=len(columns))
        descriptions = await _generate_descriptions(table, columns, llm)
        all_docs.extend(_build_documents(table, columns, descriptions))
    return all_docs


async def _run_pipeline(span: trace.Span) -> None:
    conn_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    log.info("introspecting northwind schema")
    schema = await _introspect(conn_url)
    log.info("tables found", count=len(schema))
    span.set_attribute("schema.tables", len(schema))

    all_docs = await _generate_all_documents(schema, _make_llm())

    retriever = QdrantRetriever()
    await retriever.ensure_collection()
    log.info(
        "embedding and upserting to qdrant",
        documents=len(all_docs),
        embed_model=settings.embed_model,
        collection=settings.qdrant_collection_name,
    )
    await retriever.add_documents(all_docs)
    span.set_attribute("documents.upserted", len(all_docs))
    log.info("seed complete", documents=len(all_docs))


async def seed() -> None:
    provider = init_tracing()
    try:
        with trace.get_tracer("seed").start_as_current_span("northwind-seed") as span:
            await _run_pipeline(span)
    finally:
        # BatchSpanProcessor flushes in a background thread — force it to complete
        # before the process exits, otherwise spans are silently dropped.
        provider.force_flush()
        provider.shutdown()


if __name__ == "__main__":
    asyncio.run(seed())

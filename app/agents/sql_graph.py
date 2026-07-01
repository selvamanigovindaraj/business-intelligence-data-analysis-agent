from __future__ import annotations

import json
import operator
from collections.abc import AsyncGenerator
from typing import Annotated, Any, TypedDict

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import SecretStr

from app.agents.tools.python_executor import PythonExecutor
from app.agents.tools.sql_executor import SqlExecutor
from app.agents.tools.sql_validator import validate_sql
from app.components.retriever import QdrantRetriever
from app.config import settings
from app.models import PythonCodeBlock, SqlResult, TableSchema
from app.prompts.registry import PromptRegistry

log = structlog.get_logger()

_MAX_RETRIES = 3
_UNKNOWN_ERROR = "unknown error"


class SqlState(TypedDict, total=False):
    question: str
    schemas: list[TableSchema]
    sql: str
    explanation: str
    validation_error: str | None
    execution_error: str | None
    retry_count: int
    error_history: Annotated[list[dict[str, Any]], operator.add]
    rows: list[dict[str, Any]]
    answer: str
    analyze: bool
    python_code: str
    analysis_success: bool
    analysis_stdout: str
    analysis_result: str | None
    analysis_error: str | None


def _route_after_validation(state: SqlState) -> str:
    if not state.get("validation_error"):
        return "sql_executor"
    return "sql_corrector" if state.get("retry_count", 0) < _MAX_RETRIES else "error_response"


def _route_after_explanation(state: SqlState) -> str:
    return "python_agent" if state.get("analyze") else END


def _route_after_execution(state: SqlState) -> str:
    if not state.get("execution_error"):
        return "result_explainer"
    return "sql_corrector" if state.get("retry_count", 0) < _MAX_RETRIES else "error_response"


class SqlGraph:
    """LangGraph pipeline: retriever → generator → validator → corrector* → executor → explainer."""

    def __init__(self) -> None:
        self._retriever = QdrantRetriever()
        self._executor = SqlExecutor()
        self._python_executor = PythonExecutor()
        self._prompts = PromptRegistry()
        self._llm = ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.deepseek_base_url,
            api_key=SecretStr(settings.deepseek_api_key),
            temperature=0,
        )
        # method="json_mode" avoids tool_choice, which is incompatible with DeepSeek thinking mode
        self._sql_chain = self._llm.with_structured_output(SqlResult, method="json_mode")
        self._python_chain = self._llm.with_structured_output(PythonCodeBlock, method="json_mode")
        self._graph: Any = self._build()

    def _build(self) -> Any:  # Any: CompiledStateGraph not consistently exported
        graph: StateGraph[SqlState] = StateGraph(SqlState)
        graph.add_node("schema_retriever", self._schema_retriever_node)
        graph.add_node("sql_generator", self._sql_generator_node)
        graph.add_node("sql_validator", self._sql_validator_node)
        graph.add_node("sql_corrector", self._sql_corrector_node)
        graph.add_node("sql_executor", self._sql_executor_node)
        graph.add_node("result_explainer", self._result_explainer_node)
        graph.add_node("error_response", self._error_response_node)
        graph.add_node("python_agent", self._python_agent_node)
        graph.add_node("python_executor", self._python_executor_node)
        graph.set_entry_point("schema_retriever")
        graph.add_edge("schema_retriever", "sql_generator")
        graph.add_edge("sql_generator", "sql_validator")
        graph.add_conditional_edges("sql_validator", _route_after_validation)
        graph.add_edge("sql_corrector", "sql_validator")
        graph.add_conditional_edges("sql_executor", _route_after_execution)
        graph.add_conditional_edges("result_explainer", _route_after_explanation)
        graph.add_edge("python_agent", "python_executor")
        graph.add_edge("python_executor", END)
        graph.add_edge("error_response", END)
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
        system = self._prompts.get("sql").format(schema_text=schema_text)
        result: SqlResult = await self._sql_chain.ainvoke([  # type: ignore[assignment]
            SystemMessage(content=system),
            HumanMessage(content=state["question"]),
        ])
        log.info("sql generated", table_count=len(schemas))
        return {"sql": result.sql, "explanation": result.explanation}

    def _sql_validator_node(self, state: SqlState) -> SqlState:
        error = validate_sql(state["sql"], state.get("schemas", []))
        if error:
            log.warning("sql validation failed", error=error)
        return {"validation_error": error}

    async def _sql_corrector_node(self, state: SqlState) -> SqlState:
        failed_sql = state["sql"]
        error = state.get("validation_error") or state.get("execution_error") or _UNKNOWN_ERROR
        attempt = state.get("retry_count", 0) + 1
        schema_text = "\n\n".join(s.content for s in state.get("schemas", []))
        history = state.get("error_history", [])
        history_text = "\n".join(
            f"Attempt {e['attempt']}: {e['error']!r} on SQL: {e['sql']!r}" for e in history
        ) or "None"
        system = self._prompts.get("sql_correct").format(
            history_text=history_text, schema_text=schema_text
        )
        result: SqlResult = await self._sql_chain.ainvoke(  # type: ignore[assignment]
            [
                SystemMessage(content=system),
                HumanMessage(content=f"Failed SQL:\n{failed_sql}\n\nError:\n{error}"),
            ],
            config={"metadata": {"retry_count": attempt}},
        )
        log.info("sql corrected", attempt=attempt)
        return {
            "sql": result.sql,
            "explanation": result.explanation,
            "retry_count": attempt,
            "error_history": [{"sql": failed_sql, "error": error, "attempt": attempt}],
            "validation_error": None,
            "execution_error": None,
        }

    async def _sql_executor_node(self, state: SqlState) -> SqlState:
        # SqlExecutor is a plain class, not a LangChain BaseTool, so this call carries no
        # callback-based tracing of its own — the "sql_executor" span comes solely from
        # LangGraph's per-node instrumentation, avoiding the duplicate-trace bug BaseTool caused.
        result = await self._executor.arun(state["sql"])
        return {"rows": result["rows"], "execution_error": result["error"]}

    async def _result_explainer_node(self, state: SqlState) -> SqlState:
        rows_text = json.dumps(state["rows"][:50], default=str)
        human = f"Question: {state['question']}\nSQL: {state['sql']}\nResults:\n{rows_text}"
        response = await self._llm.ainvoke([
            SystemMessage(content=self._prompts.get("sql_explain").format()),
            HumanMessage(content=human),
        ])
        answer: str = response.content  # type: ignore[assignment]
        log.info("result explained", answer_len=len(answer))
        return {"answer": answer}

    async def _python_agent_node(self, state: SqlState) -> SqlState:
        rows_text = json.dumps(state["rows"][:50], default=str)
        human = f"Question: {state['question']}\nResults:\n{rows_text}"
        result: PythonCodeBlock = await self._python_chain.ainvoke(  # type: ignore[assignment]
            [
                SystemMessage(content=self._prompts.get("python_agent").format()),
                HumanMessage(content=human),
            ]
        )
        log.info("python code generated", description=result.expected_output_description)
        return {"python_code": result.code}

    async def _python_executor_node(self, state: SqlState) -> SqlState:
        rows_literal = json.dumps(json.dumps(state["rows"], default=str))
        script = (
            f"import json\nimport pandas as pd\n"
            f"df = pd.DataFrame(json.loads({rows_literal}))\n{state['python_code']}\nresult\n"
        )
        result = await self._python_executor.arun(script)
        log.info("python code executed", success=result.success, error=result.error)
        return {
            "analysis_success": result.success,
            "analysis_stdout": result.stdout,
            "analysis_result": result.result,
            "analysis_error": result.error,
        }

    async def _error_response_node(self, state: SqlState) -> SqlState:
        attempts = state.get("retry_count", 0)
        final_error = (
            state.get("execution_error") or state.get("validation_error") or _UNKNOWN_ERROR
        )
        answer = (
            f"Could not generate a valid answer after {attempts} attempt(s). "
            f"Last error: {final_error}"
        )
        log.warning("max retries exceeded", attempts=attempts, final_error=final_error)
        return {"answer": answer}

    async def stream(self, question: str, analyze: bool = False) -> AsyncGenerator[str, None]:
        sql = ""
        explanation = ""
        rows: list[dict[str, Any]] = []
        async for chunk in self._graph.astream(
            {
                "question": question,
                "retry_count": 0,
                "error_history": [],
                "analyze": analyze,
            },
            stream_mode="updates",
        ):
            if "sql_generator" in chunk:
                sql = chunk["sql_generator"].get("sql", "")
                explanation = chunk["sql_generator"].get("explanation", "")
            if "sql_corrector" in chunk:
                sql = chunk["sql_corrector"].get("sql", sql)
                explanation = chunk["sql_corrector"].get("explanation", explanation)
            if "sql_executor" in chunk:
                rows = chunk["sql_executor"].get("rows", [])
            if "result_explainer" in chunk:
                node_out = chunk["result_explainer"]
                payload = {
                    "event": "result",
                    "sql": sql,
                    "explanation": explanation,
                    "rows": rows,
                    "answer": node_out.get("answer", ""),
                }
                yield f"data: {json.dumps(payload, default=str)}\n\n"
            if "python_executor" in chunk:
                node_out = chunk["python_executor"]
                payload = {
                    "event": "analysis",
                    "success": node_out.get("analysis_success", False),
                    "stdout": node_out.get("analysis_stdout", ""),
                    "result": node_out.get("analysis_result"),
                    "error": node_out.get("analysis_error"),
                }
                yield f"data: {json.dumps(payload, default=str)}\n\n"
            if "error_response" in chunk:
                node_out = chunk["error_response"]
                payload = {"event": "error", "message": node_out.get("answer", "")}
                yield f"data: {json.dumps(payload)}\n\n"
        yield 'data: {"event": "done"}\n\n'

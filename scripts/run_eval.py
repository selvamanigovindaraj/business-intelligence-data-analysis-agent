#!/usr/bin/env python
"""RAGAS baseline evaluation against the 26-question golden set.

Flow:
  1. Upload golden_v1.json as a Phoenix dataset (reused on repeat runs).
  2. Collect SqlGraph outputs for all questions (async, one pass before experiment).
  3. async_run_experiment — task (lookup) + evaluators (code + RAGAS LLM) run together,
     so Phoenix shows real evaluation scores against each task run.
  4. Saves raw JSON + CSV to evals/.

Usage:
    make eval                         # full 26 questions
    make eval LIMIT=5                 # smoke-test: first 5 questions
    uv run python scripts/run_eval.py --seed-only
    uv run python scripts/run_eval.py --eval-only
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import types as _types
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Compatibility shim: ragas 0.4 hard-imports langchain_community.chat_models.vertexai
# and langchain_community.llms.vertexai which were removed in langchain_community 0.4+.
_VERTEXAI_STUBS: dict[str, dict[str, type]] = {
    "langchain_community.chat_models.vertexai": {"ChatVertexAI": type("ChatVertexAI", (), {})},
    "langchain_community.llms.vertexai": {"VertexAI": type("VertexAI", (), {})},
}
for _mod_name, _attrs in _VERTEXAI_STUBS.items():
    if _mod_name not in sys.modules:
        _stub = _types.ModuleType(_mod_name)
        for _k, _v in _attrs.items():
            setattr(_stub, _k, _v)
        sys.modules[_mod_name] = _stub

import openai  # noqa: E402
import structlog  # noqa: E402
from phoenix.client.experiments import create_evaluator  # noqa: E402

from app.agents.sql_graph import SqlGraph  # noqa: E402
from app.config import settings  # noqa: E402

log = structlog.get_logger()

DATASET_NAME = "northwind-golden-v1"
EXPERIMENT_NAME = "ragas-baseline-v1"
GOLDEN_PATH = ROOT / "evals" / "golden_v1.json"
RESULTS_PATH = ROOT / "evals" / "results_baseline.json"
SCORES_PATH = ROOT / "evals" / "scores_baseline.csv"

# default max_tokens=1024 truncates faithfulness JSON on long answers
_RAGAS_MAX_TOKENS = 4096

_Score = tuple[float | None, str | None, str | None]


def _phoenix_http_url() -> str:
    parts = urlparse(settings.phoenix_collector_endpoint)
    return urlunparse(parts._replace(netloc=f"{parts.hostname}:6006"))


def _empty_output() -> dict[str, Any]:
    return {"sql": "", "rows": [], "answer": "", "retrieved_contexts": [], "error": None}


# ── Phase 1: collect pipeline outputs ──────────────────────────────────────

async def _run_one(graph: SqlGraph, question: str) -> dict[str, Any]:
    state: dict[str, Any] = await graph._graph.ainvoke({"question": question})
    schemas = state.get("schemas", [])
    return {
        "sql": state.get("sql", ""),
        "rows": state.get("rows", [])[:20],
        "answer": state.get("answer", ""),
        "retrieved_contexts": [s.content for s in schemas],
        "error": None,
    }


async def collect_pipeline_outputs(
    graph: SqlGraph, golden: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for item in golden:
        q = item["question"]
        log.info("running question", id=item["id"], total=len(golden), question=q[:70])
        try:
            results[q] = await _run_one(graph, q)
        except Exception as exc:  # noqa: BLE001
            log.warning("question failed", id=item["id"], error=str(exc))
            results[q] = {**_empty_output(), "error": str(exc)}
    return results


# ── Phase 2: Phoenix dataset ────────────────────────────────────────────────

def get_or_create_dataset(client: Any, golden: list[dict[str, Any]]) -> Any:
    try:
        ds = client.datasets.get_dataset(name=DATASET_NAME)
        log.info("reusing dataset", name=DATASET_NAME, examples=ds.example_count)
        return ds
    except Exception as exc:  # noqa: BLE001
        log.debug("dataset not found, creating", name=DATASET_NAME, reason=str(exc))

    ds = client.datasets.create_dataset(
        name=DATASET_NAME,
        dataset_description=(
            "26-question golden set: 8 simple / 10 medium / 8 complex SQL queries on Northwind"
        ),
        inputs=[{"question": q["question"], "difficulty": q["difficulty"]} for q in golden],
        outputs=[
            {"reference_sql": q["reference_sql"], "reference_answer": q["reference_answer"]}
            for q in golden
        ],
        metadata=[{"reference_tables": q["reference_tables"], "id": q["id"]} for q in golden],
        input_keys=["question", "difficulty"],
        output_keys=["reference_sql", "reference_answer"],
        metadata_keys=["reference_tables", "id"],
    )
    log.info("created dataset", name=DATASET_NAME, examples=ds.example_count)
    return ds


# ── Phase 3a: code evaluators (deterministic, no LLM) ──────────────────────

@create_evaluator(kind="CODE", name="sql_generated")
def eval_sql_generated(output: dict[str, Any]) -> _Score:
    sql = (output or {}).get("sql", "")
    score = float(bool(sql and sql.strip()))
    return (score, "yes" if score else "no", None)


@create_evaluator(kind="CODE", name="answer_complete")
def eval_answer_complete(output: dict[str, Any]) -> _Score:
    answer = (output or {}).get("answer", "")
    score = float(len(answer.strip()) > 10)
    return (score, "complete" if score else "empty", None)


@create_evaluator(kind="CODE", name="rows_returned")
def eval_rows_returned(output: dict[str, Any]) -> _Score:
    rows = (output or {}).get("rows") or []
    score = float(len(rows) > 0)
    return (score, "yes" if score else "no", f"{len(rows)} rows")


# ── Phase 3b: RAGAS scorer helpers (module-level, capture no state) ─────────
# Business logic lives here; thin @create_evaluator wrappers in _build_ragas_evaluators()
# close over metric instances (unavoidable — @create_evaluator requires inline async defs
# that capture the pre-constructed metric objects).

async def _score_answer_relevancy(ar: Any, question: str, answer: str) -> _Score:
    results = await ar.abatch_score([{"user_input": question, "response": answer}])
    score: float = results[0].value
    return (score, "relevant" if score >= 0.7 else "irrelevant", None)


async def _score_faithfulness(
    fa: Any, question: str, answer: str, rows: list[Any]
) -> _Score:
    contexts = [json.dumps(r, default=str) for r in rows] or ["(no rows returned)"]
    results = await fa.abatch_score([{
        "user_input": question,
        "response": answer,
        "retrieved_contexts": contexts,
    }])
    score: float = results[0].value
    return (score, "faithful" if score >= 0.7 else "unfaithful", None)


async def _score_context_precision(
    cp: Any, question: str, answer: str, schemas: list[str]
) -> _Score:
    results = await cp.abatch_score([{
        "user_input": question,
        "response": answer,
        "retrieved_contexts": schemas,
    }])
    score: float = results[0].value
    return (score, "precise" if score >= 0.5 else "imprecise", None)


def _build_ragas_evaluators() -> list[Any]:
    """Instantiate RAGAS metrics once, wrap in thin @create_evaluator closures."""
    from ragas.embeddings import OpenAIEmbeddings as RagasOpenAIEmbeddings
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecisionWithoutReference,
        Faithfulness,
    )

    # AsyncOpenAI required — abatch_score calls agenerate() internally
    llm_client = openai.AsyncOpenAI(
        base_url=settings.deepseek_base_url,
        api_key=settings.deepseek_api_key,
    )
    embed_client = openai.AsyncOpenAI(
        base_url=settings.embed_base_url,
        api_key=settings.nebius_api_key,
    )
    eval_llm = llm_factory(
        model=settings.llm_model,
        provider="openai",
        client=llm_client,
        max_tokens=_RAGAS_MAX_TOKENS,
    )
    eval_emb = RagasOpenAIEmbeddings(client=embed_client, model=settings.embed_model)

    ar = AnswerRelevancy(llm=eval_llm, embeddings=eval_emb)
    fa = Faithfulness(llm=eval_llm)
    cp = ContextPrecisionWithoutReference(llm=eval_llm)

    @create_evaluator(kind="LLM", name="answer_relevancy")
    async def eval_answer_relevancy(
        input: dict[str, Any],  # noqa: A002
        output: dict[str, Any] | None,
    ) -> _Score:
        answer = (output or {}).get("answer", "")
        if not answer:
            return (None, None, "no answer")
        return await _score_answer_relevancy(ar, input["question"], answer)

    @create_evaluator(kind="LLM", name="faithfulness")
    async def eval_faithfulness(
        input: dict[str, Any],  # noqa: A002
        output: dict[str, Any] | None,
    ) -> _Score:
        out = output or {}
        answer = out.get("answer", "")
        if not answer:
            return (None, None, "no answer")
        return await _score_faithfulness(fa, input["question"], answer, out.get("rows") or [])

    @create_evaluator(kind="LLM", name="context_precision")
    async def eval_context_precision(
        input: dict[str, Any],  # noqa: A002
        output: dict[str, Any] | None,
    ) -> _Score:
        out = output or {}
        answer = out.get("answer", "")
        if not answer:
            return (None, None, "no answer")
        schemas = out.get("retrieved_contexts") or ["(no schemas retrieved)"]
        return await _score_context_precision(cp, input["question"], answer, schemas)

    return [eval_answer_relevancy, eval_faithfulness, eval_context_precision]


# ── Main ────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RAGAS eval against the Northwind golden set")
    parser.add_argument("--seed-only", action="store_true", help="Only upload dataset, skip eval")
    parser.add_argument("--eval-only", action="store_true", help="Skip dataset seed, run eval only")
    parser.add_argument("--limit", type=int, default=0, help="Evaluate first N questions (0=all)")
    parser.add_argument(
        "--concurrency", type=int, default=3,
        help="Parallel evaluator calls per run (default: 3, lower = fewer token errors)",
    )
    return parser.parse_args()


async def _main_async(
    golden: list[dict[str, Any]],
    dataset: Any,
    concurrency: int,
    phoenix_url: str,
) -> None:
    from phoenix.client import AsyncClient
    from phoenix.client.experiments import async_run_experiment

    async_client = AsyncClient(base_url=phoenix_url)

    log.info("initialising SqlGraph")
    graph = SqlGraph()

    log.info("collecting pipeline outputs", total=len(golden))
    all_outputs = await collect_pipeline_outputs(graph, golden)
    n_ok = sum(1 for v in all_outputs.values() if not v.get("error"))
    log.info("pipeline complete", ok=n_ok, total=len(all_outputs))

    async def task(input: dict[str, Any]) -> dict[str, Any]:  # noqa: A002
        return all_outputs.get(input["question"], _empty_output())

    evaluators = [
        eval_sql_generated,
        eval_answer_complete,
        eval_rows_returned,
        *_build_ragas_evaluators(),
    ]

    log.info("starting experiment", name=EXPERIMENT_NAME, evaluators=len(evaluators),
             concurrency=concurrency)
    await async_run_experiment(
        dataset=dataset,
        task=task,
        evaluators=evaluators,
        experiment_name=EXPERIMENT_NAME,
        experiment_description=(
            "SqlGraph: schema_retriever → sql_generator → sql_executor → result_explainer"
        ),
        experiment_metadata={
            "llm_model": settings.llm_model,
            "embed_model": settings.embed_model,
        },
        concurrency=concurrency,
        client=async_client,
    )


def main() -> None:
    args = _parse_args()

    try:
        import pandas  # noqa: F401
        from ragas.metrics.collections import AnswerRelevancy as _  # noqa: F401
    except ImportError as exc:
        log.error("missing dependency", error=str(exc), hint="uv pip install ragas pandas")
        return

    with open(GOLDEN_PATH) as f:
        golden: list[dict[str, Any]] = json.load(f)

    if args.limit:
        golden = golden[: args.limit]
        log.info("golden questions loaded", count=len(golden), limit=args.limit)
    else:
        log.info("golden questions loaded", count=len(golden))

    from phoenix.client import Client

    phoenix_url = _phoenix_http_url()
    log.info("connecting to Phoenix", url=phoenix_url)
    client = Client(base_url=phoenix_url)

    if not args.eval_only:
        dataset = get_or_create_dataset(client, golden)
    else:
        dataset = client.datasets.get_dataset(name=DATASET_NAME)
        log.info("reusing dataset", name=DATASET_NAME)

    if args.seed_only:
        return

    asyncio.run(_main_async(golden, dataset, concurrency=args.concurrency, phoenix_url=phoenix_url))


if __name__ == "__main__":
    main()

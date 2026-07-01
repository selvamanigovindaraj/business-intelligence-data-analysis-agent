---
name: verify-agent
description: End-to-end verification loop for the BI data-analysis agent. Calls the API with a condition-targeting payload, validates logs, fixes gaps, runs clean-code-review + ponytail, and loops up to 4 times until the pipeline is clean. Accepts an optional argument naming the condition/path to exercise (e.g. "sql corrector retry", "validation error", "happy path"). If no argument is given, derive the condition from recent unstaged changes.
---

# verify-agent

## Purpose

Drive the agent through a specific code path, verify it behaves as intended via
structured logs, fix anything that breaks, then confirm the code meets style and
design standards. The loop runs **at most 4 times**. If a step fails, fix it and
restart from Step 1 — never hand back partially-verified work.

---

## Before the loop: orient

1. Read `ARGUMENTS` (the condition to exercise). If empty, run `git diff --name-only`
   and `git diff` to infer the condition from unstaged changes. State your conclusion
   in one sentence.
2. Identify the target endpoint and the agent path being exercised:
   - **SQL stream path** → `POST /api/v1/chat/stream`, body `{"question": "<...>"}`,
     nodes: `schema_retriever → sql_generator → sql_validator → [sql_corrector*] →
     sql_executor → result_explainer` or `→ error_response`.
   - **General chat path** → `POST /api/v1/chat`, body `{"session_id": "test",
     "message": "<...>"}`, routing through `adaptive_router.py`.
3. Check whether the server is reachable:
   ```bash
   curl -s http://localhost:8000/health
   ```
   - **Running** → proceed.
   - **Not running** → start it in background:
     ```bash
     uvicorn app.main:app --reload > /tmp/agent-verify.log 2>&1 &
     sleep 3 && curl -s http://localhost:8000/health
     ```
   - **Docker** → `make up` then check health.

---

## Loop (repeat up to 4 times, label each iteration)

### Step 1 — Fire the payload

Choose a question/message that targets the condition. Examples:

| Condition | Payload question |
|-----------|-----------------|
| Happy path (valid SQL) | `"How many orders were placed in 1997?"` |
| Validation error + correction | `"Show me sales from the bogus_table"` |
| Max-retry exhaustion | Use `validate_sql` mock **or** craft a question whose answer would reference a non-existent table; confirm `validate_sql` always returns an error first by checking the validator logic. |
| Execution error | Provide a syntactically valid but runtime-failing query topic. |

**SQL stream endpoint:**
```bash
curl -s -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "<QUESTION>"}' 2>&1
```
Capture the full SSE output. Record every `event` field seen.

**General chat endpoint:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "verify-run", "message": "<MESSAGE>"}' 2>&1
```

### Step 2 — Validate logs and SSE output

**Determine expected signals for the condition:**

| Condition | Expected log keys (structlog) | Expected SSE events |
|-----------|------------------------------|---------------------|
| Happy path | `schemas retrieved`, `sql generated`, `result explained` | `result`, `done` |
| Validation error → correction | `sql validation failed`, `sql corrected` (×N), `result explained` | `result`, `done` |
| Max retries exhausted | `sql validation failed` ×(_MAX_RETRIES+1_), `max retries exceeded` | `error`, `done` |
| Execution error → correction | `sql corrected`, `result explained` | `result`, `done` |

**Check server logs:**
```bash
# If running locally:
cat /tmp/agent-verify.log | grep -E "(schemas retrieved|sql generated|sql validation|sql corrected|result explained|max retries|execution_error)"

# If Docker:
make logs 2>&1 | tail -100 | grep -E "(schemas retrieved|sql generated|sql validation|sql corrected|result explained|max retries)"
```

**Pass criteria:**
- All expected log keys appear for the target condition.
- No unexpected `error` events when the happy path is being tested.
- The SSE stream ends with `{"event": "done"}`.

**If payload is not triggering the intended condition:**
- Adjust the question so it reliably hits the path (e.g., reference a known non-existent
  table name for the correction path; use a known valid question for the happy path).
- Re-fire Step 1 with the updated payload before continuing.

**If logs are insufficient** (expected key absent, no visibility into a node):
- Open `app/agents/sql_graph.py` and add the missing `structlog` call.
- Rules: one `log.info(...)` at the start of each node naming the node and key state
  fields; one `log.warning(...)` on any error branch. No `print()`.
- Re-fire Step 1 after adding logs.

### Step 3 — Fix pipeline failures

If Step 1 returned a non-200 HTTP status, an exception traceback in the log, or
an unexpected SSE `{"event": "error"}` on the happy path:

1. Read the traceback in full.
2. Identify the root cause (not the symptom) — check every caller of the failing
   function before editing.
3. Apply the minimal fix. Run tests to confirm:
   ```bash
   uv run pytest tests/test_sql_graph.py -x -q
   ```
4. If tests fail, fix them too (mock changes must mirror the code change).
5. Restart from **Step 1**.

### Step 4 — Code quality gate

Run both checks against every file touched in this session:

```bash
# clean-code-review
```
Invoke `/clean-code-review` on the changed files.

```bash
uv run ruff check app/agents/sql_graph.py
uv run mypy app/agents/sql_graph.py
```

**Ponytail ladder check (apply mentally to every change made):**
1. Does this addition need to exist? (YAGNI)
2. Is there an existing helper/pattern? (DRY)
3. Is it the shortest diff that works?
4. Any nested function, module-level mutable, or `print()` introduced?

If any check finds a violation: fix it, re-run Step 3 tests, then restart from **Step 1**.

---

## Exit conditions

**Success** — After a full pass of Steps 1-4 with no failures: report the
iteration number, the SSE events observed, the log keys confirmed, and any
fixes made. State which files were changed.

**Max iterations reached** — After 4 full loops without a clean pass: report
what remains broken, what was tried, and what the next human action should be.
Do not hide partial results.

---

## Hard rules

- Never skip a step because the previous run looked close.
- Never `--no-verify` or bypass `ruff`/`mypy`.
- Never add `print()` — only `structlog`.
- Fix the root cause, not the symptom — grep callers before editing.
- `_arun` on LangChain tools is private; use `.arun()`.
- `async def` nodes with no `await` must be made `def`.
- One new `structlog` call per added node; no log call explains WHAT the code does.

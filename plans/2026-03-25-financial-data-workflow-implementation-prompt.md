# Financial Data Workflow Implementation Prompt

> **Hand this entire file to the implementing agent as a single prompt. Do not stop at analysis. Implement the feature end-to-end, run the required checks, and report concrete results.**

---

## Your mission

Implement a repo-native financial disclosure monitor inside the existing `prefect_marimo_starter` repository.

The feature must:

- monitor configured Japanese companies for cash-relevant disclosures
- reuse TDnet announcement discovery already present in this repo
- retrieve matching EDINET filing data
- extract cash metrics from XBRL first
- compute deterministic cash-runway outputs
- flag fundraising and liquidity language with deterministic rules
- persist normalized data into PostgreSQL
- run as a Prefect flow inside a Marimo notebook

This is **not** a standalone app. It must fit this repository’s existing architecture and conventions.

You have two authoritative documents in this repo:

1. **Spec:** `docs/specs/financial_data_workflow.md`
2. **Implementation plan:** `plans/2026-03-25-financial-data-workflow-implementation-plan.md`

Read both files in full before writing code.

When they differ, **the implementation plan takes precedence** because it resolves repo-specific decisions and exact execution order.

---

## Critical repo conventions

These are mandatory.

### 1. Notebook decorator stacking

```python
# CORRECT
@app.function
@task(retries=2, retry_delay_seconds=30)
def my_task():
    ...

# WRONG
@task
@app.function
def my_task():
    ...
```

### 2. Notebook contract

Every production notebook must follow this structure:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [...]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup:
    from prefect import task, flow
    from shared_utils.config import get_settings
    from shared_utils.prefect_notifications import notify_on_failure

    SETTINGS = get_settings()

# tasks

@app.function
@task(...)
def my_task():
    ...

# flow

@app.function
@flow(name="...", log_prints=True, on_failure=[notify_on_failure])
def run_...(...) -> dict:
    ...

# edit cells

@app.cell
def _():
    import marimo as mo
    return (mo,)

@app.cell
def _(mo):
    if mo.app_meta().mode == "edit":
        ...
    return

# script cell

@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        result = run_...(...)
        print(result)
    return

if __name__ == "__main__":
    app.run()
```

### 3. Import strategy

- Never use `sys.path.append(...)`.
- Import repo packages directly, for example:
  - `from services.financial_monitor.financial_monitor_config import ...`
  - `from shared_utils.config import get_settings`
- Assume the repo is installed in editable mode.

### 4. Scope guardrails

For v1:

- one notebook only:
  - `notebooks/financial_monitor/financial_monitor_daily_pipeline.py`
- no backfill notebook
- no transcript ingestion
- no integration tests
- no Docker or standalone service process

### 5. Naming rules

- feature service modules must use the `financial_monitor_*.py` prefix
- tests must use `test_financial_monitor_*.py`
- tables must use `tblFinancialMonitor*`
- indexes must use `idxTblFinancialMonitor*` or equivalent repo-consistent CamelCase naming

### 6. Paths

- temp or scratch artifacts must live under `tmp/financial_monitor/`
- durable feature workspace paths must be repo-local
- reports must be written under `reports/financial_monitor/`

### 7. Testing model

- unit tests only
- mock external dependencies
- no live TDnet scraping tests
- no live EDINET tests
- notebook verification is manual via `marimo edit`

---

## Repo-specific design decisions you must follow

These are already resolved. Do not re-open them unless the codebase forces a deviation:

1. Use one daily notebook flow in v1.
2. Default `financial_monitor_database_url` to `postgresql://localhost:5432/workflow_app`.
3. Use `windows-process-pool` for deployment.
4. Use `Asia/Tokyo` for the feature schedule and report timezone.
5. Resolve the EDINET key in this order:
   1. Prefect Secret block `financial-monitor-edinet-api-key`
   2. environment variable `EDINET_API_KEY`
   3. fail fast
6. XBRL is the primary numeric source in v1.
7. HTML and PDF are allowed for context and intent-flagging support, not as the primary numeric source.

---

## Reference files to study before coding

Read these concrete repo examples before implementation:

- `AGENTS.md`
- `docs/specs/financial_data_workflow.md`
- `plans/2026-03-25-financial-data-workflow-implementation-plan.md`
- `notebooks/ir/ir_webchanges_monitor.py`
- `notebooks/tdnet/tdnet_announcement_scraper.py`
- `src/services/tdnet/tdnet_announcement_scraper.py`
- `src/shared_utils/config.py`
- `src/shared_utils/database.py`
- `tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py`
- `tests/unit/ir_monitor/test_ir_monitor_notebook_flow.py`
- `tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py`
- `tests/unit/x_monitor/test_x_monitor_settings.py`

Use these files as the repo-native pattern library. Do not invent a parallel architecture.

---

## Execution protocol

Work through the implementation plan task by task, in order.

For each task:

1. Read the task in the implementation plan.
2. Write the failing test first.
3. Run the targeted test and confirm it fails for the expected reason.
4. Implement the minimum code to make that task pass.
5. Re-run the targeted test.
6. Run `ruff` on changed files.
7. Continue to the next task.

Do not skip ahead unless a later task is blocked by an earlier design issue.

If the plan needs a deviation:

- keep the deviation minimal
- make the code change
- document the deviation in `plans/2026-03-25-financial-data-workflow-review.md`

---

## Files you are expected to create or modify

Follow the implementation plan exactly. The main file groups are:

- settings and config:
  - `.env.example`
  - `src/shared_utils/config.py`
  - `config/financial_monitor/financial_monitor_targets.example.yaml`
- services:
  - `src/services/financial_monitor/`
- migrations:
  - `migrations/financial_monitor/`
- notebook:
  - `notebooks/financial_monitor/financial_monitor_daily_pipeline.py`
- docs and deployment references:
  - `docs/financial_monitor/financial_monitor_setup.md`
  - `prefect.yaml`
  - `README.md`
  - `docs/ADDING_FLOWS.md`
- tests:
  - `tests/unit/financial_monitor/`
  - `tests/fixtures/financial_monitor/`

Do not add transcript or backfill files in this implementation.

---

## Verification requirements

You must run verification before claiming completion.

### Targeted checks during implementation

Use the exact commands from the implementation plan after each task.

### Final required checks

At minimum, run:

```bash
uv run pytest tests/unit/financial_monitor -v
uv run pytest tests/unit/test_config.py -v
uv run ruff check src/services/financial_monitor src/shared_utils/config.py notebooks/financial_monitor tests/unit/financial_monitor
uv run marimo check notebooks/financial_monitor/financial_monitor_daily_pipeline.py
```

If any of these fail, fix the issue and re-run.

### Manual smoke checks

If the feature reaches the notebook/deployment stage, also run:

```bash
uv run python notebooks/financial_monitor/financial_monitor_daily_pipeline.py
uv run marimo edit notebooks/financial_monitor/financial_monitor_daily_pipeline.py
```

If a smoke check cannot be completed in this environment, say so explicitly and explain why.

---

## Implementation quality bar

Your implementation must:

- keep notebook code orchestration-focused
- keep parsing and persistence logic in service modules
- use typed models across service boundaries when practical
- avoid passing non-serializable live clients across Prefect task boundaries
- prefer deterministic, testable logic over cleverness
- keep the first slice small and shippable

Do not:

- add transcripts
- add backfill
- add integration tests
- create a standalone app package
- switch to `flow.serve(...)`
- bypass the repo’s notebook-first structure

---

## Final response format

When implementation is complete, respond with:

1. A short summary of what was implemented.
2. The exact files created or modified.
3. The verification commands you ran and whether they passed.
4. Any deviations from the plan, with reasons.
5. Any remaining risks or manual follow-ups.

If you were blocked, say exactly where and why.

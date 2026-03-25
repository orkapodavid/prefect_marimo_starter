# Financial Data Workflow Review Context

This file is the handoff context for a reviewer inspecting the implemented
financial monitor feature in `prefect_marimo_starter`.

It is intentionally more specific than the original implementation prompt. The
goal is to help a reviewing agent separate:

- planned design from actual shipped behavior
- expected local-environment caveats from real defects
- review-worthy code paths from incidental local artifacts

## Review Scope

The implemented feature is a repo-native financial disclosure monitor for
configured Japanese companies. The shipped slice includes:

- one production notebook flow at
  `notebooks/financial_monitor/financial_monitor_daily_pipeline.py`
- TDnet announcement discovery reused via the existing TDnet service
- EDINET document discovery and download support
- XBRL-first cash metric extraction
- deterministic runway calculation and deterministic intent flags
- PostgreSQL persistence with `tblFinancialMonitor*` naming
- deployment/docs updates and unit-test coverage under
  `tests/unit/financial_monitor/`

This is still v1. The following are intentionally out of scope:

- transcript ingestion
- backfill notebook/deployment
- integration tests
- standalone service process

## High-Signal Files To Inspect

Read these first:

1. `AGENTS.md`
2. `docs/specs/financial_data_workflow.md`
3. `plans/2026-03-25-financial-data-workflow-implementation-plan.md`
4. `plans/2026-03-25-financial-data-workflow-review.md`
5. `notebooks/financial_monitor/financial_monitor_daily_pipeline.py`
6. `src/services/financial_monitor/financial_monitor_edinet_client.py`
7. `src/services/financial_monitor/financial_monitor_models.py`
8. `src/services/financial_monitor/financial_monitor_database.py`
9. `src/services/financial_monitor/financial_monitor_tdnet_adapter.py`
10. `src/services/financial_monitor/financial_monitor_xbrl_parser.py`
11. `src/shared_utils/config.py`
12. `tests/unit/financial_monitor/test_financial_monitor_notebook_flow.py`
13. `tests/unit/financial_monitor/test_financial_monitor_edinet_client.py`
14. `tests/unit/test_config.py`

Read these as supporting context:

1. `notebooks/ir/ir_webchanges_monitor.py`
2. `notebooks/tdnet/tdnet_announcement_scraper.py`
3. `src/services/tdnet/tdnet_announcement_scraper.py`
4. `docs/financial_monitor/financial_monitor_setup.md`
5. `prefect.yaml`
6. `README.md`

## What Changed Relative To The Original Plan

The feature follows the plan at a high level, but there were a few notable
implementation-time adjustments and post-implementation hardening steps.

### 1. Per-task commits were skipped

- The plan called for a git commit after each task.
- No task-by-task commits were created because the worktree already contained
  unrelated changes and the user did not request history changes.
- Review should therefore focus on file content and behavior, not commit
  boundaries.

### 2. Script-mode smoke execution still differs from the deployed path, but less

- The plan required `uv run python notebooks/financial_monitor/financial_monitor_daily_pipeline.py`
  to remain a valid manual smoke check.
- The repository does not track
  `config/financial_monitor/financial_monitor_targets.yaml`; it tracks only the
  example config.
- The script entrypoint still has two explicit modes:
  - if the tracked config exists, it runs the real decorated Prefect flow with
    `environment="prod"` and `dry_run=False`
  - if the tracked config is missing, it falls back to the tracked example
    config for a repo-local smoke path
- The simplification pass reduced the fallback divergence:
  - both modes now reuse the same notebook-level orchestration helper
  - the fallback path still uses
    `config/financial_monitor/financial_monitor_targets.example.yaml`
  - the fallback path still uses `dry_run=True`
  - the fallback path still executes task `.fn()` bodies so local smoke checks
    do not depend on a working local Prefect API server
  - artifact writing now goes through the same
    `write_financial_monitor_artifacts` task body instead of a separate manual
    artifact-write branch
- The deployed Prefect flow entrypoint remains unchanged; the difference is now
  limited to invocation mode and fallback inputs.
- Reviewer focus:
  confirm this divergence is well-contained and does not accidentally alter the
  real deployment behavior.

### 3. EDINET handling was hardened and then simplified into the service layer

The first implementation pass exposed real-world EDINET behavior not fully
captured by the initial fixtures. The following hardening changes were added:

- EDINET base host corrected to `https://api.edinet-fsa.go.jp/api/v2`
  instead of the older `disclosure2` host
- EDINET API error payload handling now inspects JSON `statusCode/message`
- request retry/backoff covers `429`, `5xx`, and transport errors
- normalized EDINET records now carry `form_code`, `securities_code`,
  `has_csv`, `csv_download_url`, and raw payload fields
- nullable EDINET text fields are coerced to empty strings before model
  validation because live EDINET responses can return `null` for fields such as
  `edinetCode`, `filerName`, and `docDescription`
- EDINET candidate selection is now disclosure-scoped instead of issuer-wide:
  only issuers with TDnet results-like matches are considered, and the EDINET
  side is limited to XBRL-bearing securities-report style filings
- XBRL fact selection is now context-aware and prefers current consolidated
  reporting-period facts instead of returning the first matching tag anywhere in
  the instance document
- notebook download logic now uses the hardened EDINET client for zip/pdf/csv
  retrieval instead of ad hoc `requests.get` calls
- after the simplification pass, TDnet-scoped EDINET selection logic now lives
  in `src/services/financial_monitor/financial_monitor_edinet_client.py`
  instead of being reimplemented inline in the notebook task

Reviewer focus:

- validate that the EDINET client behavior matches the repo’s intended secret
  resolution and download semantics
- verify the null-handling and CSV support are correct and not overfit to one
  observed payload
- verify that the TDnet-to-EDINET scoping logic is narrow enough to exclude
  unrelated issuer filings without dropping legitimate result filings
- verify that the XBRL context ranking is robust enough for real EDINET
  instance documents with multiple periods and non-consolidated contexts

### 4. Runtime/report path wrappers were simplified away

- `FinancialMonitorRuntimePaths` and `FinancialMonitorArtifactPaths` were only
  being instantiated and immediately converted back into dictionaries or path
  strings.
- The simplification pass removed those wrappers and kept runtime/artifact path
  handling as plain dictionaries.

Reviewer focus:

- confirm the simpler path handling still preserves repo-local path semantics
- confirm no Prefect serialization assumptions were relying on the deleted
  wrappers

### 5. Repo-root `.env` is now a supported local EDINET fallback path

- The agreed runtime order is still:
  1. Prefect Secret block `financial-monitor-edinet-api-key`
  2. environment variable `EDINET_API_KEY`
  3. fail fast
- `resolve_edinet_api_key()` now behaves differently depending on execution
  context:
  - inside a Prefect flow/task run, it uses Prefect Secret first and then the
    actual process environment
  - outside a Prefect run context, it may load the repo-root `.env` as a
    standalone-local convenience for smoke checks and one-off scripts
- Broken Prefect Secret resolution is no longer swallowed broadly. Missing block
  is allowed to fall through to env resolution, but non-missing block load/get
  failures now surface as configuration errors instead of being silently masked
  by a worker-local `.env`.

Reviewer focus:

- confirm the secret resolution order is still correct
- confirm repo-root `.env` loading is now actually local-only convenience, not
  a production behavior change

### 6. Shared settings were relaxed to tolerate local extra env vars

- Adding `EDINET_API_KEY` to the repo-root `.env` initially broke
  `get_settings()` because `pydantic-settings` rejected unknown env keys as
  extras.
- `src/shared_utils/config.py` now sets `extra="ignore"` in `Settings`.
- This was necessary so local service-specific env vars do not break unrelated
  settings loads.

Reviewer focus:

- determine whether `extra="ignore"` is acceptable repo-wide
- specifically assess the tradeoff between local convenience and silently
  ignoring env var typos

## Local Environment Notes For Review

These are not feature bugs by themselves:

- A gitignored repo-root `.env` may exist locally and may contain
  `EDINET_API_KEY`.
- Do not print or echo secret values in review output.
- `reports/financial_monitor/` may contain locally generated smoke artifacts.
- `uv.lock` may show incidental drift from local `uv`/`marimo` runs and should
  be assessed separately from the feature logic.

## Verified State At Time Of This Handoff

The following commands were run successfully in this workspace after the latest
EDINET and config hardening changes:

```bash
uv run pytest tests/unit/financial_monitor -v
uv run pytest tests/unit/test_config.py -v
uv run ruff check src/services/financial_monitor src/shared_utils/config.py notebooks/financial_monitor tests/unit/financial_monitor tests/unit/test_config.py
uv run marimo check notebooks/financial_monitor/financial_monitor_daily_pipeline.py
```

Additional live EDINET smoke verification was also run successfully using this
repo’s `resolve_edinet_api_key()` path:

```bash
uv run python - <<'PY'
from datetime import date, timedelta

from services.financial_monitor.financial_monitor_edinet_client import (
    FinancialMonitorEdinetClient,
    resolve_edinet_api_key,
)

api_key = resolve_edinet_api_key()
filing_date = date.today() - timedelta(days=1)
while filing_date.weekday() >= 5:
    filing_date -= timedelta(days=1)

client = FinancialMonitorEdinetClient(api_key=api_key, timeout=30)
documents = client.list_documents_by_date(filing_date)
print(f"filing_date={filing_date.isoformat()} count={len(documents)}")
if documents:
    first = documents[0]
    print(
        "first_document="
        f"{first.document_id} "
        f"edinet={first.edinet_code or '<blank>'} "
        f"xbrl={first.has_xbrl} "
        f"pdf={first.has_pdf} "
        f"csv={first.has_csv}"
    )
PY
```

Observed result on March 25, 2026:

- filing date queried: `2026-03-24`
- documents returned: `467`
- first document observed:
  `S100XRAN edinet=E12448 xbrl=True pdf=True csv=True`

This live check is valuable because it exercises:

- repo-root `.env` EDINET fallback
- real EDINET JSON endpoint selection
- live normalization of mixed EDINET rows

## Reviewer Tasks

This is a review-and-verify task, not an implementation task.

Do not make code changes unless the user explicitly asks for a fix pass after
review.

### Review objectives

Check the implementation for:

- requirement misses versus the spec and implementation plan
- notebook contract violations versus repo conventions
- Prefect serialization or orchestration mistakes
- database schema and naming mismatches
- misleading or incomplete tests
- misleading docs or deployment references
- places where the smoke path diverges materially from the deployed path
- places where the EDINET/config hardening introduced new risk

### Required verification

Run these fresh and record exact outcomes:

```bash
uv run pytest tests/unit/financial_monitor -v
uv run pytest tests/unit/test_config.py -v
uv run ruff check src/services/financial_monitor src/shared_utils/config.py notebooks/financial_monitor tests/unit/financial_monitor tests/unit/test_config.py
uv run marimo check notebooks/financial_monitor/financial_monitor_daily_pipeline.py
```

### Required workflow execution checks

1. Notebook script path:

```bash
uv run python notebooks/financial_monitor/financial_monitor_daily_pipeline.py
```

2. Direct flow call against the tracked example config:

```bash
uv run python - <<'PY'
from notebooks.financial_monitor.financial_monitor_daily_pipeline import (
    run_financial_monitor_daily_pipeline,
)

result = run_financial_monitor_daily_pipeline(
    config_path="config/financial_monitor/financial_monitor_targets.example.yaml",
    environment="dev",
    dry_run=True,
)
print(result)
PY
```

3. If a real config file exists locally, attempt one non-dry-run execution:

```bash
uv run python - <<'PY'
from pathlib import Path

from notebooks.financial_monitor.financial_monitor_daily_pipeline import (
    run_financial_monitor_daily_pipeline,
)

config_path = Path("config/financial_monitor/financial_monitor_targets.yaml")
if config_path.exists():
    result = run_financial_monitor_daily_pipeline(
        config_path=str(config_path),
        environment="prod",
        dry_run=False,
    )
    print(result)
else:
    print("SKIPPED: real config file not present")
PY
```

4. If the local repo-root `.env` contains `EDINET_API_KEY`, attempt one direct
   EDINET client sanity check without printing the secret:

```bash
uv run python - <<'PY'
from datetime import date, timedelta

from services.financial_monitor.financial_monitor_edinet_client import (
    FinancialMonitorEdinetClient,
    resolve_edinet_api_key,
)

api_key = resolve_edinet_api_key()
filing_date = date.today() - timedelta(days=1)
while filing_date.weekday() >= 5:
    filing_date -= timedelta(days=1)

documents = FinancialMonitorEdinetClient(api_key=api_key).list_documents_by_date(
    filing_date
)
print(f"filing_date={filing_date.isoformat()} count={len(documents)}")
PY
```

If any workflow run fails, capture:

- the exact command
- the exact error
- whether the failure is a real defect, an environment blocker, or an expected
  limitation documented above

## Desired Review Output

Respond in this order:

1. **Findings**
   - concrete issues first
   - ordered by severity
   - file references and line references where possible
2. **Workflow run results**
   - each command and whether it passed, failed, or was skipped
3. **Verification summary**
   - pytest, ruff, marimo, and live-EDINET summary
4. **Open questions or assumptions**
   - only when needed
5. **Residual risks**
   - anything not fully covered by the checks

If there are no findings, say that explicitly and still include the workflow
run and verification summary.

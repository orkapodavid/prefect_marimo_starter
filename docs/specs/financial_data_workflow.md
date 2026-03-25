# Spec: Repo-fit financial data workflow for Japanese disclosure monitoring

Converted from `docs/specs/Financial data workflow.docx` and rewritten to match this repository's notebook-first Prefect + Marimo architecture.

Task-by-task implementation is tracked separately in `plans/2026-03-25-financial-data-workflow-implementation-plan.md`.

## Goal

Add a repo-native workflow that monitors cash-related disclosures and management intent for Japanese listed companies by combining:

- TDnet announcement discovery
- EDINET filing retrieval
- XBRL-first metric extraction
- deterministic intent flagging for fundraising and liquidity language
- PostgreSQL persistence plus Prefect artifacts and alerts

The implementation must fit this repo instead of introducing a separate standalone app.

## Resolved decisions before implementation

These decisions are fixed for the first implementation so the work can proceed without inventing architecture mid-stream.

1. **V1 is a single notebook flow**
   - The first release uses one notebook only:
     - `notebooks/financial_monitor/financial_monitor_daily_pipeline.py`
   - Historical backfill remains a future phase. There is no separate backfill notebook or deployment in v1.

2. **V1 reuses the existing app database footprint**
   - Add `financial_monitor_database_url`, but default it to the current repo database:
     - `postgresql://localhost:5432/workflow_app`
   - Keep tables feature-namespaced with `tblFinancialMonitor*` names.
   - If the dataset grows materially later, the feature can be moved to its own database without changing table names.

3. **Deployment follows the existing Windows worker path**
   - Use `windows-process-pool`.
   - Use `Asia/Tokyo` for financial-monitor schedules and report timestamps.
   - Add one weekday daily deployment in `prefect.yaml`.

4. **EDINET secret resolution is explicit**
   - Resolution order:
     1. Prefect Secret block `financial-monitor-edinet-api-key`
     2. environment variable `EDINET_API_KEY`
     3. fail fast with a clear configuration error

5. **Transcript support is off by default**
   - Transcript ingestion is not implemented in v1.
   - The spec preserves an extension path for licensed transcript sources later, but there is no transcript fetcher, parser, table, or deployment in the first slice.

6. **Durable and temporary paths are repo-local**
   - Runtime workspace root:
     - `data/financial_monitor/<environment>/`
   - Human-facing run summaries:
     - `reports/financial_monitor/<environment>/`
   - Temporary extraction or debug artifacts:
     - `tmp/financial_monitor/`

7. **Numeric extraction is XBRL-first**
   - XBRL is the only trusted numeric source in v1.
   - HTML and PDF text may contribute operator context and intent flags, but they are not the primary source for cash metrics in the first implementation.

## Repo-specific adaptation summary

The source document is a generic Prefect workflow spec. This repo needs a narrower, opinionated version:

1. Flows must live inside Marimo notebooks with `@app.function` before `@task` or `@flow`.
2. Shared Python logic belongs under `src/services/`, not in a separate top-level application package.
3. TDnet fetching should reuse the existing scraper under `src/services/tdnet/`.
4. Runtime defaults should follow `src/shared_utils/config.py`.
5. Flow-level failures should use `shared_utils.prefect_notifications.notify_on_failure`.
6. Deployments should point directly to notebook entrypoints in `prefect.yaml`.
7. Database objects must follow the repo naming rules: tables with `tblCamelCase`, indexes with `idxCamelCase`.
8. Testing remains unit-test-first. Do not introduce live scraping integration tests in the first implementation.

## Scope

### In scope for v1

- Discover candidate disclosures from TDnet for configured companies and disclosure types
- Retrieve matching EDINET filing metadata and download associated XBRL/PDF assets
- Persist raw downloaded documents to repo-local storage
- Extract cash, cash equivalents, and cash flow fields from XBRL when available
- Compute a simple cash runway metric from extracted values plus deterministic burn-rate rules
- Flag management commentary related to fundraising, liquidity, or capital policy using deterministic rules
- Persist normalized filing, metric, and signal records into PostgreSQL
- Publish Prefect markdown artifacts and repo-local run summaries

### Out of scope for v1

- Historical backfill notebook or deployment
- Transcript ingestion
- Docker or Kubernetes deployment
- A separate API or web UI
- Live end-to-end tests against TDnet or EDINET
- LLM-first analysis of commentary
- Audio ingestion and transcription

## First implementation slice

The first implementation should produce one production-ready daily notebook flow plus the service and test surface it depends on:

- one notebook:
  - `notebooks/financial_monitor/financial_monitor_daily_pipeline.py`
- one feature service package:
  - `src/services/financial_monitor/`
- one feature config example:
  - `config/financial_monitor/financial_monitor_targets.example.yaml`
- one feature setup doc:
  - `docs/financial_monitor/financial_monitor_setup.md`
- one deployment entry:
  - `financial-monitor-daily-prod`

Everything else stays explicitly deferred until the first slice is stable.

## Proposed repo layout for v1

```text
config/
  financial_monitor/
    financial_monitor_targets.example.yaml

docs/
  financial_monitor/
    financial_monitor_setup.md

migrations/
  financial_monitor/
    env.py
    script.py.mako
    versions/
      <timestamp>_create_financial_monitor_schema.py

notebooks/
  financial_monitor/
    financial_monitor_daily_pipeline.py

src/
  services/
    financial_monitor/
      __init__.py
      financial_monitor_artifacts.py
      financial_monitor_cash_metrics.py
      financial_monitor_config.py
      financial_monitor_database.py
      financial_monitor_document_store.py
      financial_monitor_edinet_client.py
      financial_monitor_intent_flags.py
      financial_monitor_models.py
      financial_monitor_tdnet_adapter.py
      financial_monitor_xbrl_parser.py

tests/
  fixtures/
    financial_monitor/
      edinet/
      tdnet/
      xbrl/
  unit/
    financial_monitor/
      __init__.py
      conftest.py
      test_financial_monitor_cash_metrics.py
      test_financial_monitor_config.py
      test_financial_monitor_database.py
      test_financial_monitor_deployment_docs.py
      test_financial_monitor_edinet_client.py
      test_financial_monitor_intent_flags.py
      test_financial_monitor_notebook_contract.py
      test_financial_monitor_notebook_flow.py
      test_financial_monitor_settings.py
      test_financial_monitor_tdnet_adapter.py
      test_financial_monitor_xbrl_parser.py
```

## Notebook contract

The production notebook must follow the same contract used elsewhere in this repo.

Required structure:

- PEP 723 header with inline dependencies
- `import marimo`
- `__generated_with = "0.18.4"` or the current repo version
- `app = marimo.App(width="medium")`
- `with app.setup:` for shared imports
- `SETTINGS = get_settings()` in the setup scope
- `@app.function` before every `@task` or `@flow`
- `@flow(..., on_failure=[notify_on_failure])`
- `mo.app_meta().mode == "edit"` cells for interactive controls
- `mo.app_meta().mode == "script"` cell for production execution
- `if __name__ == "__main__": app.run()`

Operational constraints:

- Tasks should pass plain values, `Path`s, or typed Pydantic models across task boundaries.
- Do not pass live HTTP sessions, SQLAlchemy sessions, or parser objects between tasks.
- Reusable logic lives under `src/services/financial_monitor/`.
- Keep notebook code focused on orchestration and presentation, not parsing internals.

## Main notebook flow

Create a unified notebook entrypoint at:

`notebooks/financial_monitor/financial_monitor_daily_pipeline.py`

It should expose one primary flow:

```python
@app.function
@flow(
    name="financial-monitor-daily-pipeline",
    log_prints=True,
    on_failure=[notify_on_failure],
)
def run_financial_monitor_daily_pipeline(
    config_path: str = "./config/financial_monitor/financial_monitor_targets.yaml",
    filing_date: str | None = None,
    environment: str = "prod",
    dry_run: bool = False,
) -> dict:
    ...
```

### Required notebook tasks

Define the orchestration steps inside the notebook and push reusable logic into service modules:

1. `load_financial_monitor_config`
   - Load and validate the feature config.

2. `resolve_runtime_paths`
   - Resolve per-environment workspace and report paths.
   - Create required directories under `data/financial_monitor/<environment>/` and `reports/financial_monitor/<environment>/`.

3. `fetch_tdnet_candidates`
   - Reuse `src/services/tdnet/tdnet_announcement_scraper.py`.
   - Normalize titles, company codes, dates, and document URLs into workflow models.

4. `fetch_edinet_candidates`
   - Query EDINET by date using the resolved API key.
   - Match documents to tracked companies or TDnet-derived candidates.

5. `download_source_documents`
   - Save XBRL, PDF, and HTML files under the feature workspace.
   - Return a deterministic download manifest.

6. `extract_cash_metrics`
   - Parse XBRL into typed metric models.

7. `compute_cash_runway`
   - Calculate runway from extracted metrics and deterministic burn-rate logic.

8. `flag_management_intent`
   - Apply deterministic phrase and regex rules to filing text.

9. `persist_financial_snapshot`
   - Upsert filing metadata, extracted metrics, and intent signals into PostgreSQL.

10. `write_financial_monitor_artifacts`
    - Write Markdown and JSON summaries to the report directory and register a Prefect markdown artifact.

### Edit-mode behavior

In `marimo edit`, the notebook should provide:

- a config-path input
- a filing-date input
- an environment selector
- a dry-run toggle
- a run button
- a preview table for matched filings, extracted metrics, and intent flags

### Script-mode behavior

In `script` mode, the notebook should run the primary flow with repo-local defaults so `uv run python notebooks/financial_monitor/financial_monitor_daily_pipeline.py` remains a valid manual smoke check.

## Reuse of existing repo components

The implementation should deliberately build on existing code:

- `src/services/tdnet/tdnet_announcement_scraper.py`
  - keep TDnet announcement retrieval centralized
- `src/shared_utils/config.py`
  - add feature defaults here instead of introducing a second settings system
- `src/shared_utils/database.py`
  - extend or reuse existing database helpers where it reduces duplication
- `src/shared_utils/prefect_notifications.py`
  - keep flow-level failure behavior consistent with the rest of the repo
- `notebooks/tdnet/tdnet_announcement_scraper.py`
  - use as the notebook-pattern reference for task and flow structure
- `notebooks/ir/ir_webchanges_monitor.py`
  - use as the reference for a service-backed production notebook with artifacts and failure notifications

## Data model for v1

Use dedicated financial-monitor tables in PostgreSQL.

Suggested first-pass schema:

- `tblFinancialMonitorCompanies`
  - company code, EDINET code, display name, exchange, active flag
- `tblFinancialMonitorFilings`
  - company reference, source system, document ID, filing date, title, source URL, local raw path
- `tblFinancialMonitorCashMetrics`
  - filing reference, period end, currency, cash, operating cash flow, investing cash flow, financing cash flow, monthly burn, runway months
- `tblFinancialMonitorIntentSignals`
  - filing reference, signal type, matched phrase, excerpt, source section, match rule

Suggested indexes:

- `idxTblFinancialMonitorFilingsCompanyCodeFilingDate`
- `idxTblFinancialMonitorFilingsDocumentId`
- `idxTblFinancialMonitorCashMetricsFilingId`
- `idxTblFinancialMonitorIntentSignalsFilingIdSignalType`

## Parsing strategy

### TDnet

- Use the existing TDnet scraper for announcement discovery.
- Add a thin adapter layer in `financial_monitor_tdnet_adapter.py` to:
  - filter relevant disclosure categories
  - normalize company identifiers
  - map result rows into workflow-specific models

### EDINET

- Add a small client module in `financial_monitor_edinet_client.py`.
- Resolve the API key using the explicit order defined above.
- Normalize EDINET responses into typed service models instead of passing raw API payloads through the notebook.

### XBRL and documents

- Prefer XBRL extraction for all numeric metrics.
- Record which tags were used for each extracted metric.
- Treat HTML/PDF parsing as context enrichment for intent flags and operator review, not as the primary numeric source.

### Intent analysis

- Start with deterministic keyword sets and regex rules.
- Keep the rule set editable in config so analysts can tune phrasing without code changes.
- Defer LLM summaries until the deterministic path is stable and well tested.

## Configuration and runtime defaults

Add the following settings under `src/shared_utils/config.py` with these exact defaults:

```python
# Financial Monitor
financial_monitor_database_url: str = Field(default="postgresql://localhost:5432/workflow_app")
financial_monitor_config_path: Path = Field(
    default=Path("./config/financial_monitor/financial_monitor_targets.yaml")
)
financial_monitor_workspace_dir: Path = Field(default=Path("./data/financial_monitor"))
financial_monitor_reports_dir: Path = Field(default=Path("./reports/financial_monitor"))
financial_monitor_schedule_cron: str = Field(default="0 21 * * 1-5")
financial_monitor_timezone: str = Field(default="Asia/Tokyo")
financial_monitor_report_timezone: str = Field(default="Asia/Tokyo")
financial_monitor_default_runway_threshold_months: int = Field(default=12)
financial_monitor_enable_transcripts: bool = Field(default=False)
financial_monitor_edinet_api_key_block_name: str = Field(
    default="financial-monitor-edinet-api-key"
)
```

User-facing config should follow the same high-level pattern already used by the IR monitor:

```yaml
companies:
  mitsubishi_corp:
    name: Mitsubishi Corporation
    ticker: 8058.T
    exchange: TSE
    edinet_code: E02529

runtime:
  workspace_dir: ./data/financial_monitor/prod
  schedule_cron: "0 21 * * 1-5"

defaults:
  timezone: Asia/Tokyo
  runway_threshold_months: 12

targets:
  - id: mitsubishi_corp_results
    company_id: mitsubishi_corp
    tdnet_language: japanese
    disclosure_keywords:
      - 決算短信
      - 業績予想
      - 配当予想
    include_edinet: true
    enabled: true
```

## Deployment

Add one direct deployment entry in `prefect.yaml`:

```yaml
deployments:
  - name: financial-monitor-daily-prod
    entrypoint: notebooks/financial_monitor/financial_monitor_daily_pipeline.py:run_financial_monitor_daily_pipeline
    description: "Daily financial disclosure monitor for configured Japanese companies"
    tags: [prod, financial_monitor, tdnet, edinet]
    parameters:
      config_path: "./config/financial_monitor/financial_monitor_targets.yaml"
      environment: "prod"
      dry_run: false
    work_pool:
      name: windows-process-pool
      work_queue_name: default
    schedules:
      - cron: "0 21 * * 1-5"
        timezone: "Asia/Tokyo"
```

## Testing strategy

Keep the repo's current testing discipline:

- unit tests only under `tests/unit/financial_monitor/`
- mock EDINET responses and any file downloads
- use local fixtures for TDnet HTML, EDINET JSON, and XBRL samples
- add settings/default tests in the same style as the IR and X monitor suites
- add notebook contract tests that verify decorator order, flow naming, and edit/script cells
- add deployment-doc tests that verify the new `prefect.yaml` entry and setup docs
- rely on manual notebook checks for interactive edit mode

Minimum unit-test areas:

1. settings defaults
2. config loading and runtime fallback behavior
3. TDnet candidate filtering and normalization
4. EDINET response normalization and secret resolution
5. XBRL tag extraction and fallback behavior
6. cash runway calculation edge cases
7. intent-flag rule matching
8. database upsert idempotency
9. notebook contract and orchestration wiring
10. deployment and docs references

## Future phases

These are intentionally deferred until v1 is stable:

- transcript ingestion for licensed environments
- dedicated backfill notebook and manual deployment
- separate database if the feature outgrows `workflow_app`
- richer alert routing and analyst-facing review surfaces

## Implementation handoff

This repo works best when the architectural spec and the executable implementation plan are separate:

- architectural spec:
  - `docs/specs/financial_data_workflow.md`
- executable implementation plan:
  - `plans/2026-03-25-financial-data-workflow-implementation-plan.md`

If implementation is later delegated further, the remaining plan-family files should keep the same prefix:

- `plans/2026-03-25-financial-data-workflow-master-program.md`
- `plans/2026-03-25-financial-data-workflow-implementation-prompt.md`
- `plans/2026-03-25-financial-data-workflow-review.md`

## Source references preserved from the original document

These are the source references carried forward from the original `.docx` so the rewritten spec retains the original research trail:

1. TDnet overview: <https://www.jpx.co.jp/english/equities/listing/disclosure/tdnet/index.html>
2. TDnet XBRL data specifications: <https://www.jpx.co.jp/english/equities/listing/disclosure/xbrl/03.html>
3. EDINET portal and API registration: <https://disclosure2.edinet-fsa.go.jp/week0020.aspx>
4. `edinet-python` package reference: <https://pypi.org/project/edinet-python/>
5. JPX Investor Transcript Service: <https://www.jpx.co.jp/english/markets/paid-info-listing/transcripts/index.html>
6. Prefect workflow orchestration overview referenced by the original document: <https://www.prefect.io/blog/intro-to-workflow-orchestration>
7. Cash runway formula reference carried over from the source document: <https://www.wallstreetprep.com/knowledge/cash-runway/>

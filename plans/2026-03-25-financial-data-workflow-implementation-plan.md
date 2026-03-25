# Financial Data Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a repo-native daily financial disclosure monitor for configured Japanese companies that combines TDnet discovery, EDINET retrieval, XBRL-first cash-metric extraction, deterministic intent flagging, PostgreSQL persistence, and Prefect + Marimo orchestration.

**Architecture:** Reuse this repository's notebook-first pattern instead of building a standalone app. Keep the Prefect flow entrypoint in one notebook under `notebooks/financial_monitor/`, move reusable loaders, adapters, parsers, and persistence code into `src/services/financial_monitor/`, reuse the existing TDnet service for announcement intake, and register one direct deployment in `prefect.yaml` that runs through `windows-process-pool`.

**Tech Stack:** Python 3.12, Prefect 3, Marimo, Requests, BeautifulSoup, lxml, PostgreSQL, SQLAlchemy, Alembic, PyPDF/pymupdf, pydantic, pytest, ruff

---

## Repo-specific customization summary

This implementation must follow the repo contract, not the generic source document:

1. The first release is one notebook only: `notebooks/financial_monitor/financial_monitor_daily_pipeline.py`.
2. Shared logic lives in `src/services/financial_monitor/`, not in notebook cells beyond orchestration glue.
3. TDnet retrieval must reuse `src/services/tdnet/tdnet_announcement_scraper.py`.
4. Database tables must use `tblFinancialMonitor*` and indexes must use `idxFinancialMonitor*`.
5. Settings must extend `src/shared_utils/config.py` with explicit defaults and corresponding tests.
6. Testing is unit-only plus manual notebook verification.
7. Temporary extraction files must live under `tmp/financial_monitor/`.

## Decisions already resolved

1. **Database default** — Add `financial_monitor_database_url`, defaulting to `postgresql://localhost:5432/workflow_app`.
2. **Schedule** — Daily weekday run at `0 21 * * 1-5` in `Asia/Tokyo`.
3. **EDINET secret resolution** — Prefect Secret block first, `EDINET_API_KEY` second, then hard failure.
4. **Transcripts** — Explicitly out of v1. No transcript files, tables, or tasks yet.
5. **Backfill** — Explicitly out of v1. No backfill notebook or deployment yet.

## Planned file layout

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

---

## Task 1: Add settings defaults and user-facing config scaffolding

**Files:**
- Modify: `.env.example`
- Modify: `src/shared_utils/config.py`
- Create: `config/financial_monitor/financial_monitor_targets.example.yaml`
- Create: `tests/unit/financial_monitor/__init__.py`
- Create: `tests/unit/financial_monitor/test_financial_monitor_settings.py`
- Test: `tests/unit/test_config.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from src.shared_utils.config import get_settings


def test_financial_monitor_settings_defaults():
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.financial_monitor_database_url == "postgresql://localhost:5432/workflow_app"
    assert settings.financial_monitor_config_path == Path(
        "./config/financial_monitor/financial_monitor_targets.yaml"
    )
    assert settings.financial_monitor_workspace_dir == Path("./data/financial_monitor")
    assert settings.financial_monitor_reports_dir == Path("./reports/financial_monitor")
    assert settings.financial_monitor_schedule_cron == "0 21 * * 1-5"
    assert settings.financial_monitor_timezone == "Asia/Tokyo"
    assert settings.financial_monitor_report_timezone == "Asia/Tokyo"
    assert settings.financial_monitor_default_runway_threshold_months == 12
    assert settings.financial_monitor_enable_transcripts is False
    assert (
        settings.financial_monitor_edinet_api_key_block_name
        == "financial-monitor-edinet-api-key"
    )
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/financial_monitor/test_financial_monitor_settings.py tests/unit/test_config.py -v`
Expected: FAIL because the financial-monitor settings do not exist yet.

**Step 3: Write minimal implementation**

Add the exact settings defaults from the spec to `src/shared_utils/config.py`.

Add matching env var placeholders to `.env.example`.

Create `config/financial_monitor/financial_monitor_targets.example.yaml` with this minimal structure:

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

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/financial_monitor/test_financial_monitor_settings.py tests/unit/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add .env.example src/shared_utils/config.py config/financial_monitor/financial_monitor_targets.example.yaml tests/unit/financial_monitor/__init__.py tests/unit/financial_monitor/test_financial_monitor_settings.py
git commit -m "feat: add financial monitor settings scaffold"
```

---

## Task 2: Add typed models and config loader

**Files:**
- Create: `src/services/financial_monitor/__init__.py`
- Create: `src/services/financial_monitor/financial_monitor_models.py`
- Create: `src/services/financial_monitor/financial_monitor_config.py`
- Create: `tests/unit/financial_monitor/conftest.py`
- Create: `tests/unit/financial_monitor/test_financial_monitor_config.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from services.financial_monitor.financial_monitor_config import load_financial_monitor_config


def test_load_financial_monitor_config_merges_runtime_and_company_metadata(tmp_path: Path):
    config_path = tmp_path / "financial_monitor_targets.yaml"
    config_path.write_text(
        """
companies:
  mitsubishi_corp:
    name: Mitsubishi Corporation
    ticker: 8058.T
    exchange: TSE
    edinet_code: E02529
runtime:
  workspace_dir: ./data/financial_monitor/prod
defaults:
  timezone: Asia/Tokyo
  runway_threshold_months: 12
targets:
  - id: mitsubishi_corp_results
    company_id: mitsubishi_corp
    tdnet_language: japanese
    disclosure_keywords: [決算短信]
    include_edinet: true
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_financial_monitor_config(config_path)

    assert config.runtime.workspace_dir.name == "prod"
    assert config.targets[0].company_name == "Mitsubishi Corporation"
    assert config.targets[0].ticker == "8058.T"
    assert config.targets[0].edinet_code == "E02529"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/financial_monitor/test_financial_monitor_config.py -v`
Expected: FAIL because the loader and models do not exist yet.

**Step 3: Write minimal implementation**

Create:

- `FinancialMonitorRuntime`
- `FinancialMonitorDefaults`
- `FinancialMonitorCompany`
- `FinancialMonitorTarget`
- `FinancialMonitorConfig`

Implement `load_financial_monitor_config(path: Path) -> FinancialMonitorConfig` that:

- reads YAML
- merges `companies` metadata onto targets
- preserves runtime config separately
- validates `disclosure_keywords`, `tdnet_language`, `include_edinet`, and `enabled`

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/financial_monitor/test_financial_monitor_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/financial_monitor/__init__.py src/services/financial_monitor/financial_monitor_models.py src/services/financial_monitor/financial_monitor_config.py tests/unit/financial_monitor/conftest.py tests/unit/financial_monitor/test_financial_monitor_config.py
git commit -m "feat: add financial monitor config models"
```

---

## Task 3: Add TDnet adapter, EDINET client, and document-store helpers

**Files:**
- Create: `src/services/financial_monitor/financial_monitor_tdnet_adapter.py`
- Create: `src/services/financial_monitor/financial_monitor_edinet_client.py`
- Create: `src/services/financial_monitor/financial_monitor_document_store.py`
- Create: `tests/fixtures/financial_monitor/tdnet/`
- Create: `tests/fixtures/financial_monitor/edinet/`
- Create: `tests/unit/financial_monitor/test_financial_monitor_tdnet_adapter.py`
- Create: `tests/unit/financial_monitor/test_financial_monitor_edinet_client.py`

**Step 1: Write the failing tests**

```python
def test_tdnet_adapter_filters_to_cash_relevant_titles():
    ...


def test_resolve_edinet_api_key_prefers_prefect_block_then_env(monkeypatch):
    ...
```

Expected assertions:

- TDnet adapter drops unrelated announcement titles.
- TDnet adapter returns typed candidate records with company code, title, disclosure date, and source URL.
- EDINET key resolution prefers the configured Prefect Secret block.
- EDINET key resolution falls back to `EDINET_API_KEY`.
- Document-store helper writes deterministic relative paths under `data/financial_monitor/<environment>/raw/`.

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/financial_monitor/test_financial_monitor_tdnet_adapter.py tests/unit/financial_monitor/test_financial_monitor_edinet_client.py -v`
Expected: FAIL because the adapter and client modules do not exist yet.

**Step 3: Write minimal implementation**

Implement:

- TDnet adapter that wraps `services.tdnet.tdnet_announcement_scraper`
- EDINET HTTP client with explicit timeout and typed normalization
- API key resolver with this order:
  1. Prefect Secret block
  2. `EDINET_API_KEY`
  3. `ValueError`
- document-store helpers that create:
  - `raw/tdnet/`
  - `raw/edinet/`
  - `manifests/`

Do not pass live `requests.Session` objects across task boundaries. Keep sessions inside service calls.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/financial_monitor/test_financial_monitor_tdnet_adapter.py tests/unit/financial_monitor/test_financial_monitor_edinet_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/financial_monitor/financial_monitor_tdnet_adapter.py src/services/financial_monitor/financial_monitor_edinet_client.py src/services/financial_monitor/financial_monitor_document_store.py tests/fixtures/financial_monitor/tdnet tests/fixtures/financial_monitor/edinet tests/unit/financial_monitor/test_financial_monitor_tdnet_adapter.py tests/unit/financial_monitor/test_financial_monitor_edinet_client.py
git commit -m "feat: add financial monitor intake adapters"
```

---

## Task 4: Add database schema, cash-metric logic, and intent-flag logic

**Files:**
- Create: `migrations/financial_monitor/env.py`
- Create: `migrations/financial_monitor/script.py.mako`
- Create: `migrations/financial_monitor/versions/<timestamp>_create_financial_monitor_schema.py`
- Create: `src/services/financial_monitor/financial_monitor_database.py`
- Create: `src/services/financial_monitor/financial_monitor_cash_metrics.py`
- Create: `src/services/financial_monitor/financial_monitor_intent_flags.py`
- Create: `tests/unit/financial_monitor/test_financial_monitor_database.py`
- Create: `tests/unit/financial_monitor/test_financial_monitor_cash_metrics.py`
- Create: `tests/unit/financial_monitor/test_financial_monitor_intent_flags.py`

**Step 1: Write the failing tests**

```python
def test_compute_cash_runway_returns_none_when_inputs_are_incomplete():
    ...


def test_flag_management_intent_returns_reason_codes_for_capital_raising_phrases():
    ...


def test_upsert_financial_snapshot_is_idempotent():
    ...
```

Expected assertions:

- runway returns `None` when cash or burn inputs are missing
- runway returns `12` for `cash=1200` and `monthly_burn=100`
- intent flagger emits stable `signal_type` and `match_rule` values
- database upsert does not duplicate filings when the same document ID is processed twice

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/financial_monitor/test_financial_monitor_database.py tests/unit/financial_monitor/test_financial_monitor_cash_metrics.py tests/unit/financial_monitor/test_financial_monitor_intent_flags.py -v`
Expected: FAIL because the schema, helper logic, and upsert layer do not exist yet.

**Step 3: Write minimal implementation**

Create SQLAlchemy table definitions and migration coverage for:

- `tblFinancialMonitorCompanies`
- `tblFinancialMonitorFilings`
- `tblFinancialMonitorCashMetrics`
- `tblFinancialMonitorIntentSignals`

Create deterministic helper functions for:

- `compute_monthly_burn(...)`
- `compute_cash_runway(...)`
- `flag_management_intent(...)`

Keep phrase rules in code first, but structure them so config-driven override can be added later.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/financial_monitor/test_financial_monitor_database.py tests/unit/financial_monitor/test_financial_monitor_cash_metrics.py tests/unit/financial_monitor/test_financial_monitor_intent_flags.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add migrations/financial_monitor src/services/financial_monitor/financial_monitor_database.py src/services/financial_monitor/financial_monitor_cash_metrics.py src/services/financial_monitor/financial_monitor_intent_flags.py tests/unit/financial_monitor/test_financial_monitor_database.py tests/unit/financial_monitor/test_financial_monitor_cash_metrics.py tests/unit/financial_monitor/test_financial_monitor_intent_flags.py
git commit -m "feat: add financial monitor persistence and analysis logic"
```

---

## Task 5: Add XBRL parser and notebook flow

**Files:**
- Create: `src/services/financial_monitor/financial_monitor_xbrl_parser.py`
- Create: `src/services/financial_monitor/financial_monitor_artifacts.py`
- Create: `tests/fixtures/financial_monitor/xbrl/`
- Create: `tests/unit/financial_monitor/test_financial_monitor_xbrl_parser.py`
- Create: `notebooks/financial_monitor/financial_monitor_daily_pipeline.py`
- Create: `tests/unit/financial_monitor/test_financial_monitor_notebook_contract.py`
- Create: `tests/unit/financial_monitor/test_financial_monitor_notebook_flow.py`

**Step 1: Write the failing tests**

```python
def test_extract_cash_metrics_reads_expected_xbrl_tags():
    ...


def test_financial_monitor_notebook_contains_required_flow_contract():
    ...


def test_run_financial_monitor_daily_pipeline_calls_tasks_in_order(monkeypatch):
    ...
```

Expected notebook-contract assertions:

- `@app.function` appears before `@flow(name="financial-monitor-daily-pipeline"`
- `notify_on_failure` appears in the notebook text
- `with app.setup:` exists
- `mo.app_meta().mode == "edit"` exists
- `mo.app_meta().mode == "script"` exists
- `create_markdown_artifact` or equivalent artifact-writing path exists

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/financial_monitor/test_financial_monitor_xbrl_parser.py tests/unit/financial_monitor/test_financial_monitor_notebook_contract.py tests/unit/financial_monitor/test_financial_monitor_notebook_flow.py -v`
Expected: FAIL because the parser and notebook do not exist yet.

**Step 3: Write minimal implementation**

Create:

- XBRL parser that returns a typed metric record and the tag names used
- artifact helper for JSON and Markdown run summaries
- notebook tasks:
  - `load_financial_monitor_config`
  - `resolve_runtime_paths`
  - `fetch_tdnet_candidates`
  - `fetch_edinet_candidates`
  - `download_source_documents`
  - `extract_cash_metrics`
  - `compute_cash_runway`
  - `flag_management_intent`
  - `persist_financial_snapshot`
  - `write_financial_monitor_artifacts`

Keep notebook code orchestration-only. Service modules should do the parsing and persistence work.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/financial_monitor/test_financial_monitor_xbrl_parser.py tests/unit/financial_monitor/test_financial_monitor_notebook_contract.py tests/unit/financial_monitor/test_financial_monitor_notebook_flow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/financial_monitor/financial_monitor_xbrl_parser.py src/services/financial_monitor/financial_monitor_artifacts.py tests/fixtures/financial_monitor/xbrl notebooks/financial_monitor/financial_monitor_daily_pipeline.py tests/unit/financial_monitor/test_financial_monitor_xbrl_parser.py tests/unit/financial_monitor/test_financial_monitor_notebook_contract.py tests/unit/financial_monitor/test_financial_monitor_notebook_flow.py
git commit -m "feat: add financial monitor notebook flow"
```

---

## Task 6: Add deployment docs and repo references

**Files:**
- Modify: `prefect.yaml`
- Modify: `README.md`
- Modify: `docs/ADDING_FLOWS.md`
- Create: `docs/financial_monitor/financial_monitor_setup.md`
- Create: `tests/unit/financial_monitor/test_financial_monitor_deployment_docs.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_prefect_yaml_contains_financial_monitor_deployment():
    prefect_yaml = Path("prefect.yaml").read_text(encoding="utf-8")
    assert "financial-monitor-daily-prod" in prefect_yaml
    assert (
        "notebooks/financial_monitor/financial_monitor_daily_pipeline.py:"
        "run_financial_monitor_daily_pipeline"
    ) in prefect_yaml


def test_docs_reference_financial_monitor_workflow():
    readme_text = Path("README.md").read_text(encoding="utf-8")
    setup_doc = Path("docs/financial_monitor/financial_monitor_setup.md").read_text(
        encoding="utf-8"
    )
    assert "financial monitor" in readme_text.lower()
    assert "windows-process-pool" in setup_doc
    assert "EDINET" in setup_doc
    assert "TDnet" in setup_doc
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/financial_monitor/test_financial_monitor_deployment_docs.py -v`
Expected: FAIL because the deployment and docs do not exist yet.

**Step 3: Write minimal implementation**

Add:

- one deployment entry in `prefect.yaml`
- one setup doc describing:
  - required EDINET secret
  - config file location
  - `uv run` execution
  - `marimo edit` manual verification
  - Prefect worker command using `windows-process-pool`
- README and `docs/ADDING_FLOWS.md` references to the new workflow

**Step 4: Run tests to verify it passes**

Run: `uv run pytest tests/unit/financial_monitor/test_financial_monitor_deployment_docs.py -v`
Expected: PASS

**Step 5: Run the feature test suite**

Run: `uv run pytest tests/unit/financial_monitor -v`
Expected: PASS

Manual verification:

1. `uv run python notebooks/financial_monitor/financial_monitor_daily_pipeline.py`
2. `uv run marimo edit notebooks/financial_monitor/financial_monitor_daily_pipeline.py`

**Step 6: Commit**

```bash
git add prefect.yaml README.md docs/ADDING_FLOWS.md docs/financial_monitor/financial_monitor_setup.md tests/unit/financial_monitor/test_financial_monitor_deployment_docs.py
git commit -m "feat: add financial monitor deployment docs"
```

---

Plan complete and saved to `plans/2026-03-25-financial-data-workflow-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?

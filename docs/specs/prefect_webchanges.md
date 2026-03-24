# Spec: Repo-fit Prefect + Marimo webchanges monitor for Japanese IR page changes

## Goal

Add a new Japanese IR monitoring workflow to this repository that uses:

- **Prefect 3** for orchestration, retries, logging, artifacts, and deployment
- **webchanges** for snapshot storage, filtering, and diffing
- **repo-native Marimo notebooks** as the flow entrypoint
- **shared service modules under `src/services/`** for reusable parsing and normalization logic

The result should fit the current architecture of this repo instead of introducing a separate standalone application.

## Repo-specific constraints

This spec intentionally replaces parts of the generic design so it matches the existing codebase.

1. **The flow must live in a Marimo notebook**
   - Create a new unified notebook at `notebooks/ir/ir_webchanges_monitor.py`.
   - Use `@app.function` first, then `@task` / `@flow`.
   - Use `mo.app_meta().mode` to separate edit-mode controls from script-mode execution.

2. **Reusable logic belongs in `src/services/`**
   - Do not create a separate top-level `ir_monitor/` package with its own `main.py`.
   - Put shared Python logic in `src/services/ir_monitor/`.
   - Keep imports package-based; do not use `sys.path.append(...)`.

3. **Configuration should follow existing repo patterns**
   - Runtime defaults should come from `src/shared_utils/config.py`.
   - User-editable monitor targets should live in `config/ir_monitor/`.
   - Generated runtime files should live under the repo data/report directories, not `/data/ir-monitor`.

4. **Testing must follow this repo's testing philosophy**
   - Add **unit tests only** under `tests/unit/ir_monitor/`.
   - Use local fixture files under `tests/fixtures/ir_monitor/`.
   - Do not introduce a separate integration-test suite or live website tests.
   - Notebook verification remains manual via `marimo edit`.

5. **Deployment must follow current Prefect usage**
   - Add a direct notebook entry to `prefect.yaml`.
   - Use the existing `windows-process-pool`.
   - Keep local execution available with `python notebooks/ir/ir_webchanges_monitor.py`.

## Hard requirements

1. Monitor one or more public IR pages for Japanese companies, including multiple targets for the same company.
2. Detect meaningful changes reliably across append-only lists and in-place updated documents.
3. Capture a human-readable diff summary plus structured change records suitable for downstream notification formatting.
4. Suppress notification on initial baseline creation for newly added jobs.
5. Persist webchanges state across runs in a durable workspace.
6. Support static HTML pages and optional JavaScript-rendered pages.
7. Support configured PDF monitoring when a linked PDF can change in place.
8. Preserve Japanese text correctly, including UTF-8 and Japanese date formats.
9. Use open-source Python packages only.
10. Fit this repository's notebook-first Prefect architecture.

## Scope boundaries

### In scope

- Config-driven monitoring targets
- multi-target monitoring for a single company
- HTML list-page normalization
- JSON endpoint normalization
- Optional PDF text normalization
- webchanges job/config generation
- Prefect artifact writing
- concise notifications when meaningful changes exist
- one production notebook flow plus manual edit-mode tooling

### Out of scope for the first implementation

- database persistence
- a separate web UI
- live website smoke tests
- Docker-first deployment
- replacing existing Exchange flow-state notifications

## Proposed repo layout

```text
config/
  ir_monitor/
    ir_monitor_targets.example.yaml

notebooks/
  ir/
    ir_webchanges_monitor.py

scripts/
  ir_monitor/
    ir_monitor_normalize_content.py

src/
  services/
    ir_monitor/
      __init__.py
      ir_monitor_artifacts.py
      ir_monitor_config_loader.py
      ir_monitor_dates.py
      ir_monitor_jobs_builder.py
      ir_monitor_models.py
      ir_monitor_notifier.py
      ir_monitor_report_parser.py
      ir_monitor_runner.py
      ir_monitor_urls.py
      normalizers/
        __init__.py
        ir_monitor_generic_en_ir_news.py
        ir_monitor_generic_jp_ir_news.py
        ir_monitor_generic_json_ir_feed.py

tests/
  fixtures/
    ir_monitor/
      html/
      json/
      pdf/
      reports/
  unit/
    ir_monitor/
      __init__.py
      conftest.py
      test_ir_monitor_config_loader.py
      test_ir_monitor_dates.py
      test_ir_monitor_jobs_builder.py
      test_ir_monitor_normalizers.py
      test_ir_monitor_notifier.py
      test_ir_monitor_report_parser.py
      test_ir_monitor_runner.py
```

## Architecture

### Main flow notebook

The notebook entrypoint is:

`notebooks/ir/ir_webchanges_monitor.py`

It should expose one Prefect flow. The flow must import and use `notify_on_failure` from `shared_utils.prefect_notifications` for flow-level error handling, consistent with all other notebook flows in this repo:

```python
@app.function
@flow(name="ir-webchanges-monitor", log_prints=True, on_failure=[notify_on_failure])
def run_ir_webchanges_monitor(
    config_path: str = "./config/ir_monitor/ir_monitor_targets.yaml",
    environment: str = "dev",
    workspace_dir: str | None = None,
    notify_on_no_change: bool = False,
    dry_run: bool = False,
) -> dict:
    ...
```

### Required notebook tasks

The notebook should define these tasks inside the notebook file:

1. `load_monitor_config`
   - read YAML from disk
   - validate with pydantic models from `services.ir_monitor.ir_monitor_models`

2. `prepare_workspace`
   - resolve durable workspace path
   - create:
     - `webchanges/`
     - `generated/`
     - `artifacts/`
     - `logs/`
     - `state/`
   - write generated `jobs.yaml` and `config.yaml`

3. `run_webchanges`
   - run `webchanges` as a subprocess
   - pass explicit paths for jobs/config/state
   - initialize new-job baselines without notifying
   - capture stdout/stderr/exit code

4. `parse_webchanges_output`
   - convert structured reporter output into structured records
   - fall back to raw stdout parsing when the structured sidecar is unavailable
   - preserve baseline-initialized, changed, failed, and inferred unchanged targets

5. `write_artifacts`
   - persist timestamped raw report, JSON summary, and Markdown summary
   - register useful Prefect artifacts when practical

6. `notify_if_needed`
   - notify only when meaningful changes exist unless `notify_on_no_change=True`

### Edit-mode behavior

In `marimo edit`, the notebook should provide:

- config path input
- environment selector
- dry-run toggle
- run button
- visible preview of parsed change records

### Script-mode behavior

In `script` mode, the notebook should call `run_ir_webchanges_monitor()` with a repo-local default config path.

## Service module responsibilities

### `ir_monitor_models.py`

Define pydantic models for:

- monitor defaults
- monitor targets
- company/page grouping metadata
- generated workspace metadata
- normalized item records with stable item keys
- parsed webchanges change events
- notification payloads

### `ir_monitor_config_loader.py`

Responsibilities:

- read YAML config from disk
- apply defaults to each target
- validate enum-like fields
- validate unique target IDs
- validate that duplicate monitored URLs are handled safely for webchanges job identity
- ignore disabled targets during job generation

### `ir_monitor_dates.py`

Normalize common Japanese and English date forms to `YYYY-MM-DD`, including:

- `2026年3月19日`
- `2026/03/19`
- `2026-03-19`
- `Mar 19, 2026`

### `ir_monitor_urls.py`

Responsibilities:

- convert relative links to absolute URLs
- normalize whitespace around URLs
- preserve UTF-8 text

### Normalizer modules

Implement at least:

- `ir_monitor_generic_jp_ir_news.py`
- `ir_monitor_generic_en_ir_news.py`
- `ir_monitor_generic_json_ir_feed.py`

Each module should expose a simple callable that returns normalized plain text:

```python
def normalize(content: str, page_url: str) -> str:
    ...
```

Normalized output should use one stable line per item.

Each normalized line must start with a stable item identity so the workflow can distinguish:

- a brand-new disclosure item
- an update to an existing disclosure item
- a reorder-only change that should be ignored

Recommended line shape:

```text
ITEM_KEY=<stable_key> | DATE=YYYY-MM-DD | TITLE=<title> | URL=<absolute_url> | TYPE=pdf|html|json | LANG=ja|en
```

Rules for normalized output:

- `ITEM_KEY` must be stable across runs for the same disclosure item.
- Prefer the absolute disclosure URL as the item key when available.
- If the source lacks a durable URL, derive a deterministic key from immutable source fields.
- Output must be sorted deterministically before returning text.
- The normalizer must remove cosmetic whitespace and known noisy fragments before sorting.

### `ir_monitor_jobs_builder.py`

Responsibilities:

- build one webchanges job per enabled target
- preserve company/page metadata on each generated job
- choose filters based on `target_kind`, `selector_type`, and `normalizer`
- choose diff mode by target type instead of forcing one global default
- generate `diff_filters`
- ensure duplicate monitored URLs remain unique for webchanges job identity
- emit repo-stable `jobs.yaml`
- generate commands that use the current interpreter path instead of assuming a global `python`

### `ir_monitor_runner.py`

Responsibilities:

- run `webchanges`
- pass explicit jobs/config/database paths
- support explicit baseline initialization for newly added jobs
- collect raw output and exit status
- keep subprocess behavior testable without live network calls

### `ir_monitor_report_parser.py`

Responsibilities:

- prefer a structured changed-jobs sidecar capture and use stdout parsing as a fallback
- distinguish:
  - no change
  - changed
  - failed
- preserve per-target metadata needed for company-level rollups
- extract added lines when `additions_only` is used
- extract both before/after item lines when `unified` diff mode is used
- retain raw output for artifact storage

### webchanges output format reference

The workflow should not rely on informal terminal formatting alone.

Primary parsing contract:

- generate webchanges config that emits a machine-readable changed-jobs payload for changed jobs
- the preferred source is a generated reporter path that captures webchanges changed-job metadata during the run
- persist that payload as a sidecar artifact during the same run
- treat raw stdout as a human-readable artifact and fallback parser input only

Fallback stdout parser requirements:

- handle a header line per job with the job name and status (for example `CHANGED`, `UNCHANGED`, `ERROR`)
- handle diff lines prefixed with `+` or `-`
- handle error details when a job fails to fetch or filter
- be pinned to the exact webchanges major/minor version declared in `pyproject.toml`

Refer to the [webchanges documentation](https://webchanges.readthedocs.io/) for exact output formatting. The fixture files under `tests/fixtures/ir_monitor/reports/` must contain realistic samples of each status type (changed, unchanged, error) to keep the parser testable without live network calls.

### `ir_monitor_artifacts.py`

Responsibilities:

- write timestamped files under the resolved workspace
- create:
  - `raw_report.txt`
  - `changes.json`
  - `changes.md`

### `ir_monitor_notifier.py`

Responsibilities:

- format concise notifications from parsed events
- support at least:
  - webhook or Slack-compatible webhook
  - log-only fallback
- group notifications by company first, then by target/page
- keep content notifications separate from existing flow-state notification hooks

## Configuration schema

User-facing config should live in:

`config/ir_monitor/ir_monitor_targets.yaml`

Example:

```yaml
companies:
  mitsubishi_corp:
    name: Mitsubishi Corporation
    ticker: 8058.T
    exchange: TSE
  nagase:
    name: NAGASE & Co., Ltd.
    ticker: 8012.T
    exchange: TSE

defaults:
  timezone: Asia/Tokyo
  notify_on_no_change: false
  workspace_dir: ./data/ir_monitor/prod
  schedule_cron: "0 * * * 1-5"
  report_timezone: Asia/Tokyo

targets:
  - id: mitsubishi_corp_ir_ja
    company_id: mitsubishi_corp
    page_label: Japanese IR landing page
    country: JP
    language: ja
    page_url: https://www.mitsubishicorp.com/jp/ja/ir/
    user_visible_url: https://www.mitsubishicorp.com/jp/ja/ir/
    target_kind: html_list
    use_browser: false
    selector_type: custom_script
    selector: ""
    normalizer: generic_jp_ir_news
    diff_mode: additions_only
    enabled: true
    notes: "Primary Japanese IR listing page"

  - id: nagase_ir_en
    company_id: nagase
    page_label: English IR page
    country: JP
    language: en
    page_url: https://www.nagase.co.jp/english/ir/
    user_visible_url: https://www.nagase.co.jp/english/ir/
    target_kind: html_list
    use_browser: false
    selector_type: custom_script
    selector: ""
    normalizer: generic_en_ir_news
    diff_mode: additions_only
    enabled: true

  - id: mitsubishi_corp_notice_pdf
    company_id: mitsubishi_corp
    page_label: In-place PDF notice
    country: JP
    language: ja
    page_url: https://example.com/ir/latest_notice.pdf
    user_visible_url: https://www.mitsubishicorp.com/jp/ja/ir/
    target_kind: pdf_document
    use_browser: false
    normalizer: pdf_text
    diff_mode: unified
    enabled: false
```

Required target schema rules:

- `id` must be unique across all targets.
- `companies` is optional; when present, it is keyed by `company_id` and supplies canonical `name`, `ticker`, and `exchange` metadata for any matching targets.
- `company_id` groups multiple targets that belong to the same issuer.
- `company_name` remains a valid target field for backward compatibility, but a matching `companies[company_id].name` takes precedence when both are provided.
- `page_label` is the human-readable label used in notifications and artifacts.
- `target_kind` must be an explicit enum such as `html_list`, `json_feed`, or `pdf_document`.
- `user_visible_url` is the URL shown in reports when the monitored URL is an API endpoint or a synthetic unique URL.
- `diff_mode` must default by `target_kind` but remain overrideable per target.
- JSON targets must support optional request settings such as method, headers, and body.
- PDF targets must support direct PDF URLs without browser rendering.

## Runtime paths and persistence

Persist state inside the repo-configurable data area.

Default workspace resolution:

- `workspace_dir` flow parameter if provided
- otherwise `get_settings().data_directory / "ir_monitor" / environment`

Each run should use durable directories such as:

```text
data/ir_monitor/prod/
  webchanges/
  generated/
  artifacts/
  logs/
  state/
```

This is mandatory because webchanges requires prior snapshots to compute diffs correctly.

The durable state contract must be explicit:

- generated jobs/config files may be replaced on each run
- webchanges snapshot/database files must survive across runs
- artifacts must be timestamped per run
- baseline metadata should record when a target was first initialized

## Baseline initialization

Initial baselines must be handled as a first-class workflow state, not as an accidental side effect.

Requirements:

- newly added targets must initialize a snapshot without sending a content notification
- the generated webchanges config must suppress `new` notifications and/or the runner must explicitly prepare new jobs before the main diffing pass
- existing targets must continue diffing against durable prior state
- the run summary must distinguish:
  - `baseline_initialized`
  - `unchanged`
  - `changed`
  - `failed`
- the workspace should record which targets were initialized during the run for auditability
- if unchanged targets are not emitted directly by webchanges, the parser must infer them from the enabled target set minus `baseline_initialized`, `changed`, and `failed`

## webchanges generation rules

1. One job per enabled target.
2. Multiple targets may belong to the same company; reporting must roll them up by `company_id`.
3. Default to `additions_only` for append-only list-style pages.
4. Default to `unified` for in-place mutable documents such as directly monitored PDFs.
5. Prefer direct JSON/XHR endpoints over browser rendering.
6. Use browser rendering only when `use_browser=true`.
7. Use custom normalizer execution for IR lists instead of raw HTML diffs.
8. Ensure normalized output is deterministic and already sorted before diffing.
9. If the same monitored URL is used by more than one target, generate a unique effective webchanges job URL while preserving `user_visible_url` for reporting.
10. Keep external webchanges reporters disabled by default; Prefect owns final notifications.
11. Generate commands with absolute script paths and the active interpreter path.
12. Pin the generated stdout reporter settings so fallback parsing remains stable across environments.

Example generated job shape:

```yaml
name: mitsubishi_corp_ir_ja
url: https://www.mitsubishicorp.com/jp/ja/ir/
user_visible_url: https://www.mitsubishicorp.com/jp/ja/ir/
filters:
  - execute: /absolute/path/to/python /absolute/path/to/scripts/ir_monitor/ir_monitor_normalize_content.py --normalizer generic_jp_ir_news --page-url https://www.mitsubishicorp.com/jp/ja/ir/
diff_filters:
  - additions_only
```

## Meaningful change definition

A meaningful change includes:

- a new disclosure/news item with a previously unseen `ITEM_KEY`
- a change to the normalized line of an existing `ITEM_KEY`
- a changed disclosure title
- a changed disclosure date
- a changed linked PDF URL
- a material change in monitored PDF extracted text
- new or changed entries from a monitored JSON endpoint

It does **not** include:

- a pure reorder of otherwise identical normalized item lines
- cosmetic HTML outside the monitored section
- whitespace-only changes
- random CSS hash changes
- rotating banners
- cookie text outside the normalized section
- timestamps or counters explicitly filtered as noise

## Notification behavior

Implement at least one content-notification backend plus one fallback:

- Primary: webhook or Slack-compatible webhook
- Fallback: Prefect log output only
- Optional later extension: Exchange email content notifications if needed

Short notification content should include:

- environment
- run timestamp
- number of changed companies
- number of changed targets
- company-grouped target summaries
- per-target added lines or before/after summaries depending on diff mode
- artifact path reference

Do not send the entire raw diff in the short notification by default.

Artifact summary requirements:

- `changes.json` must preserve company, target, status, diff mode, and parsed item lines
- `changes.md` must group records by company, then by target/page
- baseline-initialized targets must appear in the artifact summary without being treated as content changes

## Testing strategy for this repo

This repo uses **unit tests with fixtures** as the primary automated test strategy.

Required automated coverage:

- Japanese date normalization
- English date normalization
- relative URL to absolute URL conversion
- HTML normalizer output stability
- JSON normalizer output stability
- PDF text normalization
- deterministic sorting of normalized output
- stable item key generation
- baseline initialization without notification
- duplicate monitored URL handling in job generation
- diff mode selection by target kind
- webchanges stdout parser behavior
- structured changed-jobs payload parsing behavior
- job generation behavior
- notifier payload formatting
- runner behavior with mocked subprocess output

Use only local fixture files and mocks.

> **Convention note:** This feature introduces `tests/fixtures/ir_monitor/` for self-contained fixture data. The existing repo uses `tests/inputs/` and `tests/outputs/` for other features. The `tests/fixtures/` path is an intentional choice for fixture files that belong to a single feature and do not require the shared `inputs/outputs` directory structure.

Do not add:

- live-site tests
- a dedicated integration test suite
- notebook-specific automated tests

Manual verification should cover:

```bash
marimo edit notebooks/ir/ir_webchanges_monitor.py
uv run python notebooks/ir/ir_webchanges_monitor.py
```

## Dependency changes

Update `pyproject.toml` with pinned runtime dependencies for this feature, including:

- `webchanges` pinned to an explicit version so parser fixtures stay stable
- `playwright` as an optional dependency or clearly documented runtime requirement when browser mode is enabled

Continue using:

- `pydantic`
- `PyYAML`
- `beautifulsoup4`
- `lxml`
- `pypdf`

Notebook PEP 723 dependencies should mirror the notebook's direct runtime needs.

Runtime notes to document:

- browser-enabled targets require Playwright plus Chrome installation
- Windows execution must preserve UTF-8 output for Japanese text in both subprocess execution and captured artifacts

## Deployment requirements

Add a new deployment in `prefect.yaml`:

```yaml
# Also add to definitions.schedules in prefect.yaml:
#   hourly_weekday_tokyo: &hourly_weekday_tokyo
#     cron: "0 * * * 1-5"
#     timezone: "Asia/Tokyo"

- name: ir-webchanges-monitor-prod
  entrypoint: notebooks/ir/ir_webchanges_monitor.py:run_ir_webchanges_monitor
  description: "Monitor configured Japanese IR pages with webchanges"
  tags: [prod, ir, webchanges]
  parameters:
    config_path: "./config/ir_monitor/ir_monitor_targets.yaml"
    environment: "prod"
    notify_on_no_change: false
    dry_run: false
  work_pool: *windows_pool
  schedules:
    - *hourly_weekday_tokyo
```

Local developer execution remains:

```bash
uv run python notebooks/ir/ir_webchanges_monitor.py
```

## Deliverables

1. Repo-native Marimo notebook flow at `notebooks/ir/ir_webchanges_monitor.py`
2. Shared service modules under `src/services/ir_monitor/`
3. Example target config under `config/ir_monitor/`
4. webchanges normalizer bridge script under `scripts/ir_monitor/`
5. Unit tests plus local fixtures
6. `pyproject.toml` updates
7. `prefect.yaml` deployment entry
8. README or docs updates describing setup, local run, and browser prerequisites

## Implementation constraints

- Do not use paid APIs.
- Do not build a custom diff engine; let webchanges own fetch/filter/diff/state.
- Do not introduce `sys.path` hacks. The bridge script at `scripts/ir_monitor/ir_monitor_normalize_content.py` relies on the editable install (`uv pip install -e .`) to resolve imports from `src/services/ir_monitor/`. Always run it via `uv run` or from an activated virtualenv where the editable install is present.
- Do not assume plain `python` on PATH for generated commands; use the active interpreter path.
- Do not assume browser jobs can fetch PDFs; direct PDF monitoring must use non-browser jobs.
- Do not create a separate non-notebook flow wrapper.
- Do not start implementation until an explicit implementation plan is written and approved.

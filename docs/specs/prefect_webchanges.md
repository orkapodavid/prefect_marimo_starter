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

1. Monitor one or more public IR pages for Japanese companies.
2. Detect meaningful changes reliably.
3. Capture a human-readable diff summary.
4. Suppress notification on initial baseline creation.
5. Persist webchanges state across runs in a durable workspace.
6. Support static HTML pages and optional JavaScript-rendered pages.
7. Support configured PDF monitoring when a linked PDF can change in place.
8. Preserve Japanese text correctly, including UTF-8 and Japanese date formats.
9. Use open-source Python packages only.
10. Fit this repository's notebook-first Prefect architecture.

## Scope boundaries

### In scope

- Config-driven monitoring targets
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
   - write generated `jobs.yaml` and `config.yaml`

3. `run_webchanges`
   - run `webchanges` as a subprocess
   - pass explicit paths for jobs/config/state
   - capture stdout/stderr/exit code

4. `parse_webchanges_output`
   - convert raw stdout into structured records
   - preserve changed and failed targets

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
- generated workspace metadata
- parsed webchanges change events
- notification payloads

### `ir_monitor_config_loader.py`

Responsibilities:

- read YAML config from disk
- apply defaults to each target
- validate enum-like fields
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

Normalized output should use one stable line per item:

```text
YYYY-MM-DD | TITLE | ABSOLUTE_URL | TYPE=pdf|html|json | LANG=ja|en
```

### `ir_monitor_jobs_builder.py`

Responsibilities:

- build one webchanges job per enabled target
- choose filters based on `page_type`, `selector_type`, and `normalizer`
- generate `diff_filters`
- emit repo-stable `jobs.yaml`
- generate commands that use the current interpreter path instead of assuming a global `python`

### `ir_monitor_runner.py`

Responsibilities:

- run `webchanges`
- pass explicit jobs/config/database paths
- collect raw output and exit status
- keep subprocess behavior testable without live network calls

### `ir_monitor_report_parser.py`

Responsibilities:

- parse stdout into structured records
- distinguish:
  - no change
  - changed
  - failed
- extract added lines when `additions_only` is used
- retain raw output for artifact storage

### webchanges output format reference

The report parser must handle the text output that webchanges writes to stdout. A typical run produces output with:

- A header line per job with the job name and status (e.g., `CHANGED`, `UNCHANGED`, `ERROR`)
- For changed jobs: diff lines prefixed with `+` (added) or `-` (removed) when using `additions_only` or `unified` diff mode
- Error details when a job fails to fetch or filter

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
- keep content notifications separate from existing flow-state notification hooks

## Configuration schema

User-facing config should live in:

`config/ir_monitor/ir_monitor_targets.yaml`

Example:

```yaml
defaults:
  timezone: Asia/Tokyo
  notify_on_no_change: false
  workspace_dir: ./data/ir_monitor/prod
  schedule_cron: "0 * * * 1-5"
  report_timezone: Asia/Tokyo

targets:
  - id: mitsubishi_corp_ir_ja
    company_name: Mitsubishi Corporation
    country: JP
    language: ja
    page_url: https://www.mitsubishicorp.com/jp/ja/ir/
    page_type: html_list
    use_browser: false
    selector_type: custom_script
    selector: ""
    normalizer: generic_jp_ir_news
    diff_mode: additions_only
    enabled: true
    notes: "Primary Japanese IR listing page"

  - id: nagase_ir_en
    company_name: NAGASE & Co., Ltd.
    country: JP
    language: en
    page_url: https://www.nagase.co.jp/english/ir/
    page_type: html_list
    use_browser: false
    selector_type: custom_script
    selector: ""
    normalizer: generic_en_ir_news
    diff_mode: additions_only
    enabled: true
```

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
```

This is mandatory because webchanges requires prior snapshots to compute diffs correctly.

## webchanges generation rules

1. One job per enabled target.
2. Default to `additions_only` for list-style pages.
3. Prefer direct JSON/XHR endpoints over browser rendering.
4. Use browser rendering only when `use_browser=true`.
5. Use custom normalizer execution for IR lists instead of raw HTML diffs.
6. Keep external webchanges reporters disabled by default; Prefect owns final notifications.
7. Generate commands with absolute script paths and the active interpreter path.

Example generated job shape:

```yaml
name: mitsubishi_corp_ir_ja
url: https://www.mitsubishicorp.com/jp/ja/ir/
filters:
  - execute: /absolute/path/to/python /absolute/path/to/scripts/ir_monitor/ir_monitor_normalize_content.py --normalizer generic_jp_ir_news --page-url https://www.mitsubishicorp.com/jp/ja/ir/
diff_filters:
  - additions_only
```

## Meaningful change definition

A meaningful change includes:

- a new disclosure/news item
- a changed disclosure title
- a changed disclosure date
- a changed linked PDF URL
- a material change in monitored PDF extracted text
- new or changed entries from a monitored JSON endpoint

It does **not** include:

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
- number of changed targets
- per-target added lines
- artifact path reference

Do not send the entire raw diff in the short notification by default.

## Testing strategy for this repo

This repo uses **unit tests with fixtures** as the primary automated test strategy.

Required automated coverage:

- Japanese date normalization
- English date normalization
- relative URL to absolute URL conversion
- HTML normalizer output stability
- JSON normalizer output stability
- PDF text normalization
- webchanges stdout parser behavior
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
python notebooks/ir/ir_webchanges_monitor.py
```

## Dependency changes

Update `pyproject.toml` with pinned runtime dependencies for this feature, including:

- `webchanges`
- `playwright` as an optional dependency or clearly documented runtime requirement when browser mode is enabled

Continue using:

- `pydantic`
- `PyYAML`
- `beautifulsoup4`
- `lxml`
- `pypdf`

Notebook PEP 723 dependencies should mirror the notebook's direct runtime needs.

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
python notebooks/ir/ir_webchanges_monitor.py
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
- Do not create a separate non-notebook flow wrapper.
- Do not start implementation until an explicit implementation plan is written and approved.

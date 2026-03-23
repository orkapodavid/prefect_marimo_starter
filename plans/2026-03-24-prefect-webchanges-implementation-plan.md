# Japanese IR Webchanges Monitor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a repo-native Japanese IR monitoring workflow that runs from a Marimo notebook, uses webchanges for stateful diffing, and reports only meaningful IR page changes.

**Architecture:** The implementation keeps orchestration inside a new notebook at `notebooks/ir/ir_webchanges_monitor.py` and pushes reusable parsing, config, notification, and webchanges helper logic into `src/services/ir_monitor/`. Runtime state is stored under the repo data directory, target definitions live under `config/ir_monitor/`, and automated coverage stays in fixture-based unit tests only.

**Tech Stack:** Python 3.12, Prefect 3, Marimo, webchanges, pydantic, PyYAML, BeautifulSoup4, lxml, pypdf, pytest

---

### Task 1: Add dependency and settings scaffolding

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/shared_utils/config.py`
- Test: `tests/unit/test_config.py`
- Create: `tests/unit/ir_monitor/test_ir_monitor_settings.py`

**Step 1: Write the failing test**

```python
from src.shared_utils.config import get_settings


def test_ir_monitor_settings_defaults():
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.ir_monitor_workspace_dir.name == "ir_monitor"
    assert settings.ir_monitor_schedule_cron == "0 * * * 1-5"
    assert settings.ir_monitor_timezone == "Asia/Tokyo"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_settings.py -v`
Expected: FAIL with `AttributeError` or missing-field validation for new IR monitor settings.

**Step 3: Write minimal implementation**

Add pinned runtime dependencies and add new settings fields similar to:

```python
ir_monitor_workspace_dir: Path = Field(default=Path("./data/ir_monitor"))
ir_monitor_schedule_cron: str = Field(default="0 * * * 1-5")
ir_monitor_timezone: str = Field(default="Asia/Tokyo")
ir_monitor_webhook_url: str = Field(default="")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_settings.py tests/unit/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml src/shared_utils/config.py tests/unit/test_config.py tests/unit/ir_monitor/test_ir_monitor_settings.py
git commit -m "feat: add ir monitor dependency and settings scaffolding"
```

### Task 2: Create config models and YAML loader

**Files:**
- Create: `src/services/ir_monitor/__init__.py`
- Create: `src/services/ir_monitor/ir_monitor_models.py`
- Create: `src/services/ir_monitor/ir_monitor_config_loader.py`
- Create: `config/ir_monitor/ir_monitor_targets.example.yaml`
- Create: `tests/unit/ir_monitor/__init__.py`
- Create: `tests/unit/ir_monitor/conftest.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_config_loader.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from src.services.ir_monitor.ir_monitor_config_loader import load_monitor_config


def test_load_monitor_config_applies_defaults(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        '''
defaults:
  timezone: Asia/Tokyo
  schedule_cron: "0 * * * 1-5"
targets:
  - id: mitsubishi_corp_ir_ja
    company_name: Mitsubishi Corporation
    page_url: https://example.com/ir
    page_type: html_list
    selector_type: custom_script
    normalizer: generic_jp_ir_news
    diff_mode: additions_only
    enabled: true
''',
        encoding="utf-8",
    )

    config = load_monitor_config(config_path)

    assert config.defaults.timezone == "Asia/Tokyo"
    assert config.targets[0].language == "ja"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_config_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.ir_monitor'`.

**Step 3: Write minimal implementation**

Create pydantic models for defaults and targets, then implement:

```python
def load_monitor_config(config_path: Path) -> MonitorConfig:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return MonitorConfig.model_validate(payload)
```

Include sane defaults for `country="JP"`, `language="ja"`, and `use_browser=False`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_config_loader.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/__init__.py src/services/ir_monitor/ir_monitor_models.py src/services/ir_monitor/ir_monitor_config_loader.py config/ir_monitor/ir_monitor_targets.example.yaml tests/unit/ir_monitor/__init__.py tests/unit/ir_monitor/conftest.py tests/unit/ir_monitor/test_ir_monitor_config_loader.py
git commit -m "feat: add ir monitor config models and loader"
```

### Task 3: Add date and URL normalization helpers

**Files:**
- Create: `src/services/ir_monitor/ir_monitor_dates.py`
- Create: `src/services/ir_monitor/ir_monitor_urls.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_dates.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_urls.py`

**Step 1: Write the failing test**

```python
from src.services.ir_monitor.ir_monitor_dates import normalize_date_text
from src.services.ir_monitor.ir_monitor_urls import to_absolute_url


def test_normalize_japanese_date():
    assert normalize_date_text("2026年3月19日") == "2026-03-19"


def test_to_absolute_url():
    assert (
        to_absolute_url("/jp/ir/notice.pdf", "https://example.co.jp/jp/ir/")
        == "https://example.co.jp/jp/ir/notice.pdf"
    )
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_dates.py tests/unit/ir_monitor/test_ir_monitor_urls.py -v`
Expected: FAIL because helper modules do not exist yet.

**Step 3: Write minimal implementation**

Implement small helpers:

```python
def normalize_date_text(value: str) -> str | None:
    ...


def to_absolute_url(url: str, page_url: str) -> str:
    return urljoin(page_url, url.strip())
```

Handle Japanese and English date formats before returning ISO date text.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_dates.py tests/unit/ir_monitor/test_ir_monitor_urls.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/ir_monitor_dates.py src/services/ir_monitor/ir_monitor_urls.py tests/unit/ir_monitor/test_ir_monitor_dates.py tests/unit/ir_monitor/test_ir_monitor_urls.py
git commit -m "feat: add ir monitor date and url helpers"
```

### Task 4: Implement HTML, JSON, and PDF normalizers

**Files:**
- Create: `src/services/ir_monitor/normalizers/__init__.py`
- Create: `src/services/ir_monitor/normalizers/ir_monitor_generic_jp_ir_news.py`
- Create: `src/services/ir_monitor/normalizers/ir_monitor_generic_en_ir_news.py`
- Create: `src/services/ir_monitor/normalizers/ir_monitor_generic_json_ir_feed.py`
- Create: `tests/fixtures/ir_monitor/html/jp_ir_list.html`
- Create: `tests/fixtures/ir_monitor/html/en_ir_list.html`
- Create: `tests/fixtures/ir_monitor/json/ir_feed.json`
- Create: `tests/fixtures/ir_monitor/pdf/sample_ir_text.txt`
- Test: `tests/unit/ir_monitor/test_ir_monitor_normalizers.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from src.services.ir_monitor.normalizers.ir_monitor_generic_jp_ir_news import normalize as normalize_jp


def test_generic_jp_ir_news_normalizes_to_stable_lines():
    html = Path("tests/fixtures/ir_monitor/html/jp_ir_list.html").read_text(encoding="utf-8")
    output = normalize_jp(html, "https://example.co.jp/jp/ir/")

    assert "2026-03-19 | Notice Regarding Change of Representative Directors" in output
    assert "TYPE=pdf | LANG=ja" in output
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_normalizers.py -v`
Expected: FAIL because the normalizer package and fixtures are not ready.

**Step 3: Write minimal implementation**

Implement normalizers that:

```python
def normalize(content: str, page_url: str) -> str:
    # parse list items, normalize date text, absolutize links,
    # and return one stable line per IR item
    ...
```

Keep PDF normalization as helper logic exercised by tests without hitting live URLs.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_normalizers.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/normalizers/__init__.py src/services/ir_monitor/normalizers/ir_monitor_generic_jp_ir_news.py src/services/ir_monitor/normalizers/ir_monitor_generic_en_ir_news.py src/services/ir_monitor/normalizers/ir_monitor_generic_json_ir_feed.py tests/fixtures/ir_monitor/html/jp_ir_list.html tests/fixtures/ir_monitor/html/en_ir_list.html tests/fixtures/ir_monitor/json/ir_feed.json tests/fixtures/ir_monitor/pdf/sample_ir_text.txt tests/unit/ir_monitor/test_ir_monitor_normalizers.py
git commit -m "feat: add ir monitor content normalizers"
```

### Task 5: Add the webchanges normalizer bridge script

> **Depends on:** Task 4 (normalizers must exist before the bridge script can import them).

**Files:**
- Create: `scripts/ir_monitor/ir_monitor_normalize_content.py`
- Modify: `src/services/ir_monitor/normalizers/__init__.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_normalize_script.py`

**Step 1: Write the failing test**

```python
from pathlib import Path
import subprocess
import sys


def test_normalize_script_runs_with_generic_jp_normalizer():
    html_path = Path("tests/fixtures/ir_monitor/html/jp_ir_list.html")
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ir_monitor/ir_monitor_normalize_content.py",
            "--normalizer",
            "generic_jp_ir_news",
            "--page-url",
            "https://example.co.jp/jp/ir/",
            "--input-file",
            str(html_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "TYPE=pdf | LANG=ja" in result.stdout
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_normalize_script.py -v`
Expected: FAIL because the script does not exist yet.

**Step 3: Write minimal implementation**

Create a script that dispatches by normalizer name:

```python
NORMALIZERS = {
    "generic_jp_ir_news": normalize_generic_jp_ir_news,
    "generic_en_ir_news": normalize_generic_en_ir_news,
    "generic_json_ir_feed": normalize_generic_json_ir_feed,
}
```

Read stdin by default, with an `--input-file` option for tests.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_normalize_script.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/ir_monitor/ir_monitor_normalize_content.py src/services/ir_monitor/normalizers/__init__.py tests/unit/ir_monitor/test_ir_monitor_normalize_script.py
git commit -m "feat: add ir monitor webchanges normalizer bridge"
```

### Task 6: Build workspace preparation and job generation

**Files:**
- Create: `src/services/ir_monitor/ir_monitor_jobs_builder.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_jobs_builder.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from src.services.ir_monitor.ir_monitor_jobs_builder import build_workspace_files
from src.services.ir_monitor.ir_monitor_models import MonitorConfig, MonitorDefaults, MonitorTarget


def test_build_workspace_files_writes_jobs_and_config(tmp_path: Path):
    config = MonitorConfig(
        defaults=MonitorDefaults(timezone="Asia/Tokyo"),
        targets=[
            MonitorTarget(
                id="mitsubishi_corp_ir_ja",
                company_name="Mitsubishi Corporation",
                page_url="https://example.co.jp/jp/ir/",
                page_type="html_list",
                selector_type="custom_script",
                normalizer="generic_jp_ir_news",
                diff_mode="additions_only",
                enabled=True,
            )
        ],
    )

    workspace = build_workspace_files(config=config, workspace_dir=tmp_path)

    assert workspace.jobs_path.exists()
    assert workspace.config_path.exists()
    assert "additions_only" in workspace.jobs_path.read_text(encoding="utf-8")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_jobs_builder.py -v`
Expected: FAIL because builder logic is missing.

**Step 3: Write minimal implementation**

Implement a builder that:

```python
def build_workspace_files(config: MonitorConfig, workspace_dir: Path) -> WorkspacePaths:
    ...
```

Requirements:
- create `webchanges`, `generated`, `artifacts`, `logs`
- generate `jobs.yaml`
- generate `config.yaml`
- use `sys.executable` and absolute script paths in `execute` filters

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_jobs_builder.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/ir_monitor_jobs_builder.py tests/unit/ir_monitor/test_ir_monitor_jobs_builder.py
git commit -m "feat: add ir monitor workspace and jobs builder"
```

### Task 7: Implement subprocess runner and report parser

**Files:**
- Create: `src/services/ir_monitor/ir_monitor_runner.py`
- Create: `src/services/ir_monitor/ir_monitor_report_parser.py`
- Create: `tests/fixtures/ir_monitor/reports/webchanges_changed.txt`
- Create: `tests/fixtures/ir_monitor/reports/webchanges_no_change.txt`
- Test: `tests/unit/ir_monitor/test_ir_monitor_runner.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_report_parser.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from src.services.ir_monitor.ir_monitor_report_parser import parse_webchanges_output


def test_parse_webchanges_output_extracts_added_lines():
    raw_report = Path("tests/fixtures/ir_monitor/reports/webchanges_changed.txt").read_text(
        encoding="utf-8"
    )

    parsed = parse_webchanges_output(raw_report)

    assert parsed.changed_count == 1
    assert parsed.events[0].added_lines
    assert parsed.events[0].status == "changed"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_runner.py tests/unit/ir_monitor/test_ir_monitor_report_parser.py -v`
Expected: FAIL because the runner and parser modules do not exist yet.

**Step 3: Write minimal implementation**

Implement:

```python
def run_webchanges_command(workspace: WorkspacePaths, jobs_path: Path, config_path: Path) -> CommandResult:
    ...


def parse_webchanges_output(raw_report: str) -> ParsedMonitorReport:
    ...
```

Use mocked subprocess behavior in tests; do not call live websites.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_runner.py tests/unit/ir_monitor/test_ir_monitor_report_parser.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/ir_monitor_runner.py src/services/ir_monitor/ir_monitor_report_parser.py tests/fixtures/ir_monitor/reports/webchanges_changed.txt tests/fixtures/ir_monitor/reports/webchanges_no_change.txt tests/unit/ir_monitor/test_ir_monitor_runner.py tests/unit/ir_monitor/test_ir_monitor_report_parser.py
git commit -m "feat: add ir monitor runner and report parser"
```

### Task 8: Add artifact writing and notifications

**Files:**
- Create: `src/services/ir_monitor/ir_monitor_artifacts.py`
- Create: `src/services/ir_monitor/ir_monitor_notifier.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_artifacts.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_notifier.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from src.services.ir_monitor.ir_monitor_artifacts import write_run_artifacts


def test_write_run_artifacts_creates_timestamped_files(tmp_path: Path):
    artifact_paths = write_run_artifacts(
        workspace_dir=tmp_path,
        raw_report="raw",
        changes=[{"job_name": "mitsubishi_corp_ir_ja", "status": "changed", "added_lines": ["line"]}],
        run_label="2026-03-24T10-00-00+09-00",
    )

    assert artifact_paths.raw_report_path.exists()
    assert artifact_paths.changes_json_path.exists()
    assert artifact_paths.changes_markdown_path.exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_artifacts.py tests/unit/ir_monitor/test_ir_monitor_notifier.py -v`
Expected: FAIL because artifact and notification modules do not exist yet.

**Step 3: Write minimal implementation**

Implement:

```python
def write_run_artifacts(... ) -> ArtifactPaths:
    ...


def notify_if_needed(... ) -> NotificationResult:
    ...
```

Notifier rules:
- no notification on baseline / no-change unless enabled
- webhook first when configured
- otherwise log-only fallback

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_artifacts.py tests/unit/ir_monitor/test_ir_monitor_notifier.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/ir_monitor_artifacts.py src/services/ir_monitor/ir_monitor_notifier.py tests/unit/ir_monitor/test_ir_monitor_artifacts.py tests/unit/ir_monitor/test_ir_monitor_notifier.py
git commit -m "feat: add ir monitor artifact and notification services"
```

### Task 9: Add the unified Marimo + Prefect notebook flow

**Files:**
- Create: `notebooks/ir/ir_webchanges_monitor.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_ir_monitor_notebook_contains_prefect_flow_entrypoint():
    notebook_text = Path("notebooks/ir/ir_webchanges_monitor.py").read_text(encoding="utf-8")

    assert "@app.function" in notebook_text
    assert '@flow(name="ir-webchanges-monitor"' in notebook_text
    assert "def run_ir_webchanges_monitor(" in notebook_text
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py -v`
Expected: FAIL because the notebook file does not exist yet.

**Step 3: Write minimal implementation**

Create the notebook with:

```python
@app.function
@task
def load_monitor_config_task(...):
    ...


@app.function
@flow(name="ir-webchanges-monitor", log_prints=True, on_failure=[notify_on_failure])
def run_ir_webchanges_monitor(...):
    ...
```

Also add:
- `with app.setup` imports
- edit-mode controls
- script-mode execution block
- PEP 723 dependencies block:
  ```python
  # /// script
  # requires-python = ">=3.12"
  # dependencies = [
  #     "marimo",
  #     "prefect>=3.0.0,<4.0.0",
  #     "pydantic>=2.0.0",
  #     "pydantic-settings>=2.0.0",
  #     "pyyaml>=6.0",
  #     "webchanges",
  #     "beautifulsoup4>=4.12.0",
  #     "lxml>=5.0.0",
  #     "pypdf>=4.0.0",
  # ]
  # ///
  ```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add notebooks/ir/ir_webchanges_monitor.py tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py
git commit -m "feat: add ir monitor notebook flow"
```

### Task 10: Register deployment and update docs

**Files:**
- Modify: `prefect.yaml`
- Modify: `README.md`
- Modify: `docs/ADDING_FLOWS.md`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_prefect_yaml_contains_ir_monitor_deployment():
    prefect_yaml = Path("prefect.yaml").read_text(encoding="utf-8")
    assert "ir-webchanges-monitor-prod" in prefect_yaml
    assert "notebooks/ir/ir_webchanges_monitor.py:run_ir_webchanges_monitor" in prefect_yaml
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py -v`
Expected: FAIL because the deployment and docs are not updated yet.

**Step 3: Write minimal implementation**

Add:
- a production deployment in `prefect.yaml`
- README setup notes for `webchanges` and optional browser support
- a short flow-adding reference for the new IR notebook category

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add prefect.yaml README.md docs/ADDING_FLOWS.md tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py
git commit -m "docs: register ir monitor deployment and usage"
```

### Task 11: Run full verification before closing the branch

**Files:**
- Verify only: `pyproject.toml`
- Verify only: `notebooks/ir/ir_webchanges_monitor.py`
- Verify only: `prefect.yaml`
- Verify only: `tests/unit/ir_monitor/`

**Step 1: Run the targeted unit suite**

Run: `uv run pytest tests/unit/ir_monitor -v`
Expected: PASS

**Step 2: Run the broader regression subset**

Run: `uv run pytest tests/unit/test_config.py tests/unit/test_prefect_notifications.py -v`
Expected: PASS

**Step 3: Run static validation**

Run: `uv run ruff check src/services/ir_monitor notebooks/ir/ir_webchanges_monitor.py tests/unit/ir_monitor`
Expected: PASS

**Step 4: Run notebook validation**

Run: `uv run marimo check notebooks/ir/ir_webchanges_monitor.py`
Expected: PASS

**Step 5: Fix any issues found**

If linting or tests revealed issues during Steps 1-4, fix them and commit the fixes only. Do not re-commit work already committed in Tasks 1-10.

## Notes for the implementing engineer

- Use the customized spec in `docs/specs/prefect_webchanges.md` as the design source of truth.
- Keep the flow notebook thin; push reusable logic into `src/services/ir_monitor/`.
- Do not add live website tests.
- Do not introduce `sys.path` mutations.
- Use `sys.executable` when generating webchanges execute filters so the active environment is explicit.

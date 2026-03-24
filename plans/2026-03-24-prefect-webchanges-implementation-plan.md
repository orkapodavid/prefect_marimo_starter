# Japanese IR Webchanges Monitor Implementation Plan

> **Status:** COMPLETE
> **Completed:** 2026-03-24
> **Total tasks:** 12
> **Tasks completed:** 12
> **Deviations:** 9 (documented inline)
> **Test count:** 34 tests, all passing
> **Blocking issues:** None

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a repo-native Japanese IR monitoring workflow that runs from a Marimo notebook, uses webchanges for stateful diffing, and reports meaningful changes for one or more company IR targets.

**Architecture:** Keep orchestration inside `notebooks/ir/ir_webchanges_monitor.py` and push reusable config, normalization, webchanges, artifact, and notification logic into `src/services/ir_monitor/`. The implementation must preserve durable webchanges state across runs, use a structured changed-jobs sidecar as the primary parse source, and group reporting by company before target/page.

> **Actual:** `webchanges==3.34.2` does not expose the changed-jobs env payload assumed by the plan, so the final runtime implementation treats stdout as the diff source of truth and enriches parsed events from config metadata; the structured payload remains optional and is only used when valid sidecar data is supplied.

**Tech Stack:** Python 3.12, Prefect 3, Marimo, webchanges, pydantic, pydantic-settings, PyYAML, BeautifulSoup4, lxml, pypdf, pytest, ruff

---

### Task 1: Add dependency and settings scaffolding

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/shared_utils/config.py`
- Create: `tests/unit/ir_monitor/__init__.py`
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
    assert settings.ir_monitor_report_timezone == "Asia/Tokyo"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_settings.py -v`
Expected: FAIL with `AttributeError` or missing-field validation for new IR monitor settings.

**Step 3: Write minimal implementation**

Add pinned runtime dependencies and new settings fields similar to:

```python
ir_monitor_workspace_dir: Path = Field(default=Path("./data/ir_monitor"))
ir_monitor_schedule_cron: str = Field(default="0 * * * 1-5")
ir_monitor_timezone: str = Field(default="Asia/Tokyo")
ir_monitor_report_timezone: str = Field(default="Asia/Tokyo")
ir_monitor_webhook_url: str = Field(default="")
```

Also:
- pin `webchanges` to an explicit version in `pyproject.toml`
- add optional browser support or document it as a runtime prerequisite

> **Actual:** Pinned `webchanges==3.34.2` from the current PyPI release and added an optional `browser` extra via `webchanges[use-browser]==3.34.2`; also updated `uv.lock` because the repo uses `uv`-managed lockfiles.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_settings.py tests/unit/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml src/shared_utils/config.py tests/unit/ir_monitor/__init__.py tests/unit/test_config.py tests/unit/ir_monitor/test_ir_monitor_settings.py
git commit -m "feat: add ir monitor dependency and settings scaffolding"
```

### Task 2: Create config models and YAML loader

**Files:**
- Create: `src/services/ir_monitor/__init__.py`
- Create: `src/services/ir_monitor/ir_monitor_models.py`
- Create: `src/services/ir_monitor/ir_monitor_config_loader.py`
- Create: `config/ir_monitor/ir_monitor_targets.example.yaml`
- Create: `tests/unit/ir_monitor/conftest.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_config_loader.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

import pytest

from src.services.ir_monitor.ir_monitor_config_loader import load_monitor_config


def test_load_monitor_config_applies_target_defaults(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        '''
defaults:
  timezone: Asia/Tokyo
  report_timezone: Asia/Tokyo
targets:
  - id: mitsubishi_corp_ir_ja
    company_id: mitsubishi_corp
    company_name: Mitsubishi Corporation
    page_label: Japanese IR page
    page_url: https://example.com/ir
    user_visible_url: https://example.com/ir
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_jp_ir_news
    enabled: true
''',
        encoding="utf-8",
    )

    config = load_monitor_config(config_path)

    assert config.targets[0].country == "JP"
    assert config.targets[0].language == "ja"
    assert config.targets[0].diff_mode == "additions_only"


def test_load_monitor_config_rejects_duplicate_target_ids(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        '''
targets:
  - id: duplicate_id
    company_id: company_a
    company_name: Company A
    page_label: Page A
    page_url: https://example.com/a
    user_visible_url: https://example.com/a
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_jp_ir_news
    enabled: true
  - id: duplicate_id
    company_id: company_b
    company_name: Company B
    page_label: Page B
    page_url: https://example.com/b
    user_visible_url: https://example.com/b
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_jp_ir_news
    enabled: true
''',
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_monitor_config(config_path)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_config_loader.py -v`
Expected: FAIL with missing module or schema errors because the models and loader do not exist yet.

**Step 3: Write minimal implementation**

Create pydantic models for:
- monitor defaults
- targets using `company_id`, `page_label`, `target_kind`, and `user_visible_url`
- normalized item records
- parsed change events and notification payloads

Implement a loader like:

```python
def load_monitor_config(config_path: Path) -> MonitorConfig:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return MonitorConfig.model_validate(payload)
```

Include defaults for:
- `country="JP"`
- `language="ja"`
- `use_browser=False`
- `diff_mode="additions_only"` for `html_list`
- `diff_mode="unified"` for `pdf_document`

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_config_loader.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/__init__.py src/services/ir_monitor/ir_monitor_models.py src/services/ir_monitor/ir_monitor_config_loader.py config/ir_monitor/ir_monitor_targets.example.yaml tests/unit/ir_monitor/conftest.py tests/unit/ir_monitor/test_ir_monitor_config_loader.py
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


def test_normalize_english_date():
    assert normalize_date_text("Mar 19, 2026") == "2026-03-19"


def test_to_absolute_url_trims_whitespace():
    assert (
        to_absolute_url(" /jp/ir/notice.pdf ", "https://example.co.jp/jp/ir/")
        == "https://example.co.jp/jp/ir/notice.pdf"
    )
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_dates.py tests/unit/ir_monitor/test_ir_monitor_urls.py -v`
Expected: FAIL because helper modules do not exist yet.

**Step 3: Write minimal implementation**

Implement helpers like:

```python
def normalize_date_text(value: str) -> str | None:
    ...


def to_absolute_url(url: str, page_url: str) -> str:
    return urljoin(page_url, url.strip())
```

Handle Japanese and English date formats and preserve UTF-8 text.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_dates.py tests/unit/ir_monitor/test_ir_monitor_urls.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/ir_monitor_dates.py src/services/ir_monitor/ir_monitor_urls.py tests/unit/ir_monitor/test_ir_monitor_dates.py tests/unit/ir_monitor/test_ir_monitor_urls.py
git commit -m "feat: add ir monitor date and url helpers"
```

### Task 4: Implement deterministic normalizers with stable item keys

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


def test_generic_jp_ir_news_normalizes_to_stable_sorted_lines():
    html = Path("tests/fixtures/ir_monitor/html/jp_ir_list.html").read_text(encoding="utf-8")
    output = normalize_jp(html, "https://example.co.jp/jp/ir/")

    lines = output.splitlines()

    assert lines == sorted(lines)
    assert lines[0].startswith("ITEM_KEY=")
    assert "DATE=2026-03-19" in output
    assert "TYPE=pdf | LANG=ja" in output
```

> **Actual:** Expanded the task test coverage to include English HTML and JSON feed normalizers as well, and later added regression coverage for noisy page chrome, duplicate item keys, and split date fragments; the final HTML normalizers use repeated dated-container selection plus `ITEM_KEY` deduplication to suppress nav/footer noise while preserving stable item lines.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_normalizers.py -v`
Expected: FAIL because the normalizer package and fixtures are not ready.

**Step 3: Write minimal implementation**

Implement normalizers that:

```python
def normalize(content: str, page_url: str) -> str:
    # parse records, normalize dates and links,
    # emit ITEM_KEY-prefixed lines, remove known noise,
    # and return deterministically sorted output
    ...
```

Rules:
- prefer absolute disclosure URL for `ITEM_KEY`
- derive deterministic keys only when a durable URL does not exist
- remove cosmetic whitespace before sorting
- keep PDF normalization as text normalization logic exercised by fixtures without live URLs

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_normalizers.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/normalizers/__init__.py src/services/ir_monitor/normalizers/ir_monitor_generic_jp_ir_news.py src/services/ir_monitor/normalizers/ir_monitor_generic_en_ir_news.py src/services/ir_monitor/normalizers/ir_monitor_generic_json_ir_feed.py tests/fixtures/ir_monitor/html/jp_ir_list.html tests/fixtures/ir_monitor/html/en_ir_list.html tests/fixtures/ir_monitor/json/ir_feed.json tests/fixtures/ir_monitor/pdf/sample_ir_text.txt tests/unit/ir_monitor/test_ir_monitor_normalizers.py
git commit -m "feat: add deterministic ir monitor normalizers"
```

### Task 5: Add the webchanges normalizer bridge script

> **Depends on:** Task 4

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
    assert "ITEM_KEY=" in result.stdout
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

Requirements:
- read stdin by default
- support `--input-file` for tests
- preserve UTF-8 output
- exit non-zero on unknown normalizer names

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_normalize_script.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/ir_monitor/ir_monitor_normalize_content.py src/services/ir_monitor/normalizers/__init__.py tests/unit/ir_monitor/test_ir_monitor_normalize_script.py
git commit -m "feat: add ir monitor webchanges normalizer bridge"
```

### Task 6: Build workspace preparation and webchanges job generation

**Files:**
- Create: `src/services/ir_monitor/ir_monitor_jobs_builder.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_jobs_builder.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from src.services.ir_monitor.ir_monitor_jobs_builder import build_workspace_files
from src.services.ir_monitor.ir_monitor_models import MonitorConfig, MonitorDefaults, MonitorTarget


def test_build_workspace_files_writes_jobs_config_and_state_paths(tmp_path: Path):
    config = MonitorConfig(
        defaults=MonitorDefaults(timezone="Asia/Tokyo", report_timezone="Asia/Tokyo"),
        targets=[
            MonitorTarget(
                id="mitsubishi_corp_ir_ja",
                company_id="mitsubishi_corp",
                company_name="Mitsubishi Corporation",
                page_label="Japanese IR page",
                page_url="https://example.co.jp/jp/ir/",
                user_visible_url="https://example.co.jp/jp/ir/",
                target_kind="html_list",
                selector_type="custom_script",
                normalizer="generic_jp_ir_news",
                enabled=True,
            ),
            MonitorTarget(
                id="mitsubishi_corp_ir_ja_alt",
                company_id="mitsubishi_corp",
                company_name="Mitsubishi Corporation",
                page_label="Japanese IR page alt",
                page_url="https://example.co.jp/jp/ir/",
                user_visible_url="https://example.co.jp/jp/ir/",
                target_kind="html_list",
                selector_type="custom_script",
                normalizer="generic_jp_ir_news",
                enabled=True,
            ),
        ],
    )

    workspace = build_workspace_files(config=config, workspace_dir=tmp_path)

    assert workspace.jobs_path.exists()
    assert workspace.config_path.exists()
    assert workspace.state_dir.exists()
    jobs_text = workspace.jobs_path.read_text(encoding="utf-8")
    config_text = workspace.config_path.read_text(encoding="utf-8")
    assert "user_visible_url" in jobs_text
    assert jobs_text.count("https://example.co.jp/jp/ir/") >= 1
    assert "run_command" in config_text
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_jobs_builder.py -v`
Expected: FAIL because builder logic is missing.

**Step 3: Write minimal implementation**

Implement:

```python
def build_workspace_files(config: MonitorConfig, workspace_dir: Path) -> WorkspacePaths:
    ...
```

Requirements:
- create `webchanges`, `generated`, `artifacts`, `logs`, and `state`
- generate `jobs.yaml`
- generate `config.yaml`
- preserve company/page metadata on each job
- use `sys.executable` and absolute script paths in `execute` filters
- default diff mode by `target_kind`
- keep duplicate monitored URLs unique for webchanges job identity while preserving `user_visible_url`
- generate reporter settings for a structured changed-jobs sidecar
- suppress `new` notifications in generated config

> **Actual:** Used webchanges' documented `additions_only: true` job directive, emitted the generated jobs file as multi-document YAML (the format `webchanges` actually accepts), removed custom top-level job metadata keys that the real loader rejects, and dropped the planned `run_command` sidecar reporter after verifying that `webchanges==3.34.2` does not expose usable per-job change payloads there.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_jobs_builder.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/ir_monitor_jobs_builder.py tests/unit/ir_monitor/test_ir_monitor_jobs_builder.py
git commit -m "feat: add ir monitor workspace and jobs builder"
```

### Task 7: Implement subprocess runner and baseline initialization

**Files:**
- Create: `src/services/ir_monitor/ir_monitor_runner.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_runner.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from src.services.ir_monitor.ir_monitor_runner import run_webchanges_command
from src.services.ir_monitor.ir_monitor_models import WorkspacePaths


def test_run_webchanges_command_prepares_new_jobs_before_main_run(mocker, tmp_path: Path):
    workspace = WorkspacePaths(
        root_dir=tmp_path,
        generated_dir=tmp_path / "generated",
        jobs_path=tmp_path / "generated/jobs.yaml",
        config_path=tmp_path / "generated/config.yaml",
        state_dir=tmp_path / "state",
        artifacts_dir=tmp_path / "artifacts",
        logs_dir=tmp_path / "logs",
        changed_jobs_path=tmp_path / "artifacts/changed_jobs.json",
        baseline_metadata_path=tmp_path / "state/baselines.json",
    )
    for path in (
        workspace.generated_dir,
        workspace.state_dir,
        workspace.artifacts_dir,
        workspace.logs_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
    workspace.jobs_path.write_text("", encoding="utf-8")
    workspace.config_path.write_text("", encoding="utf-8")

    run_mock = mocker.patch("src.services.ir_monitor.ir_monitor_runner.subprocess.run")
    run_mock.side_effect = [
        mocker.Mock(returncode=0, stdout="", stderr=""),
        mocker.Mock(returncode=0, stdout="report", stderr=""),
    ]

    run_webchanges_command(workspace=workspace, new_target_ids=["mitsubishi_corp_ir_ja"])

    assert run_mock.call_count == 2
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_runner.py -v`
Expected: FAIL because the runner module does not exist yet.

**Step 3: Write minimal implementation**

Implement:

```python
def run_webchanges_command(workspace: WorkspacePaths, new_target_ids: list[str]) -> CommandResult:
    ...
```

Requirements:
- run explicit baseline initialization for new targets before the main pass
- use mocked subprocess behavior in tests
- capture stdout, stderr, exit code, and sidecar artifact paths
- keep subprocess commands deterministic and testable

> **Actual:** Added `pytest-mock` to the repo's dev dependencies because the planned test uses the `mocker` fixture; the runner invokes the console `webchanges` entrypoint (not `python -m webchanges`, which fails with `webchanges==3.34.2` in this environment), merges newly initialized baseline IDs with existing metadata instead of overwriting it, and records new baselines only after `--prepare-jobs` succeeds.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_runner.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/ir_monitor_runner.py tests/unit/ir_monitor/test_ir_monitor_runner.py
git commit -m "feat: add ir monitor subprocess runner"
```

### Task 8: Implement structured report parsing with stdout fallback

**Files:**
- Create: `src/services/ir_monitor/ir_monitor_report_parser.py`
- Create: `tests/fixtures/ir_monitor/reports/webchanges_changed_jobs.json`
- Create: `tests/fixtures/ir_monitor/reports/webchanges_changed.txt`
- Create: `tests/fixtures/ir_monitor/reports/webchanges_no_change.txt`
- Create: `tests/fixtures/ir_monitor/reports/webchanges_error.txt`
- Test: `tests/unit/ir_monitor/test_ir_monitor_report_parser.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from src.services.ir_monitor.ir_monitor_report_parser import parse_monitor_report


def test_parse_monitor_report_prefers_structured_changed_jobs_payload():
    raw_report = Path("tests/fixtures/ir_monitor/reports/webchanges_changed.txt").read_text(
        encoding="utf-8"
    )
    changed_jobs_payload = Path(
        "tests/fixtures/ir_monitor/reports/webchanges_changed_jobs.json"
    ).read_text(encoding="utf-8")

    parsed = parse_monitor_report(
        raw_report=raw_report,
        changed_jobs_payload=changed_jobs_payload,
        enabled_target_ids=["mitsubishi_corp_ir_ja", "nagase_ir_en"],
        baseline_target_ids=[],
    )

    assert parsed.changed_count == 1
    assert parsed.events[0].status == "changed"
    assert parsed.events[0].company_id == "mitsubishi_corp"
    assert parsed.unchanged_target_ids == ["nagase_ir_en"]
```

> **Actual:** Added explicit stdout-fallback tests and updated fixtures to match real `webchanges 3.34.2` console output, including duplicated summary/detail headers; the final parser ignores invalid sidecar payloads, extracts diff lines from stdout, and enriches company/page metadata from the monitor config.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_report_parser.py -v`
Expected: FAIL because the parser module and fixtures do not exist yet.

**Step 3: Write minimal implementation**

Implement:

```python
def parse_monitor_report(
    raw_report: str,
    changed_jobs_payload: str | None,
    enabled_target_ids: list[str],
    baseline_target_ids: list[str],
) -> ParsedMonitorReport:
    ...
```

Requirements:
- prefer structured changed-jobs payload when present
- fall back to stdout parsing only when sidecar data is unavailable
- parse `additions_only` and `unified` diff modes
- preserve company and target metadata
- infer unchanged targets from enabled minus baseline, changed, and failed

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_report_parser.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/ir_monitor_report_parser.py tests/fixtures/ir_monitor/reports/webchanges_changed_jobs.json tests/fixtures/ir_monitor/reports/webchanges_changed.txt tests/fixtures/ir_monitor/reports/webchanges_no_change.txt tests/fixtures/ir_monitor/reports/webchanges_error.txt tests/unit/ir_monitor/test_ir_monitor_report_parser.py
git commit -m "feat: add ir monitor report parser"
```

### Task 9: Add artifact writing and company-grouped notifications

**Files:**
- Create: `src/services/ir_monitor/ir_monitor_artifacts.py`
- Create: `src/services/ir_monitor/ir_monitor_notifier.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_artifacts.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_notifier.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from src.services.ir_monitor.ir_monitor_artifacts import write_run_artifacts


def test_write_run_artifacts_creates_company_grouped_outputs(tmp_path: Path):
    artifact_paths = write_run_artifacts(
        workspace_dir=tmp_path,
        raw_report="raw",
        parsed_events=[
            {
                "company_id": "mitsubishi_corp",
                "company_name": "Mitsubishi Corporation",
                "target_id": "mitsubishi_corp_ir_ja",
                "page_label": "Japanese IR page",
                "status": "changed",
                "diff_mode": "additions_only",
                "added_lines": ["ITEM_KEY=https://example.com/1 | DATE=2026-03-19 | TITLE=Notice"],
            },
            {
                "company_id": "nagase",
                "company_name": "NAGASE & Co., Ltd.",
                "target_id": "nagase_ir_en",
                "page_label": "English IR page",
                "status": "baseline_initialized",
                "diff_mode": "additions_only",
                "added_lines": [],
            },
        ],
        run_label="2026-03-24T10-00-00+09-00",
    )

    markdown = artifact_paths.changes_markdown_path.read_text(encoding="utf-8")

    assert artifact_paths.raw_report_path.exists()
    assert artifact_paths.changes_json_path.exists()
    assert artifact_paths.changes_markdown_path.exists()
    assert "Mitsubishi Corporation" in markdown
    assert "baseline_initialized" in markdown
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_artifacts.py tests/unit/ir_monitor/test_ir_monitor_notifier.py -v`
Expected: FAIL because artifact and notifier modules do not exist yet.

**Step 3: Write minimal implementation**

Implement:

```python
def write_run_artifacts(...) -> ArtifactPaths:
    ...


def notify_if_needed(...) -> NotificationResult:
    ...
```

Rules:
- keep `changes.json` and `changes.md` grouped by company then target
- preserve `status`, `diff_mode`, and parsed item lines
- do not notify on `baseline_initialized` or no-change unless explicitly enabled
- use webhook first when configured
- otherwise fall back to log-only output

> **Actual:** The notifier now also falls back to log-only on webhook delivery errors instead of failing the flow, and the notebook registers the generated Markdown summary as a Prefect artifact keyed by environment.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_artifacts.py tests/unit/ir_monitor/test_ir_monitor_notifier.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/ir_monitor_artifacts.py src/services/ir_monitor/ir_monitor_notifier.py tests/unit/ir_monitor/test_ir_monitor_artifacts.py tests/unit/ir_monitor/test_ir_monitor_notifier.py
git commit -m "feat: add ir monitor artifact and notification services"
```

### Task 10: Add the unified Marimo + Prefect notebook flow

**Files:**
- Create: `notebooks/ir/ir_webchanges_monitor.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_ir_monitor_notebook_contains_required_flow_contract():
    notebook_text = Path("notebooks/ir/ir_webchanges_monitor.py").read_text(encoding="utf-8")

    assert "@app.function" in notebook_text
    assert '@flow(name="ir-webchanges-monitor"' in notebook_text
    assert "notify_on_failure" in notebook_text
    assert "def load_monitor_config(" in notebook_text
    assert "def prepare_workspace(" in notebook_text
    assert "def run_webchanges(" in notebook_text
    assert "def parse_webchanges_output(" in notebook_text
    assert "def write_artifacts(" in notebook_text
    assert "def notify_if_needed(" in notebook_text
    assert 'mo.app_meta().mode == "edit"' in notebook_text
    assert 'mo.app_meta().mode == "script"' in notebook_text
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py -v`
Expected: FAIL because the notebook file does not exist yet.

**Step 3: Write minimal implementation**

Create the notebook with:
- PEP 723 dependency block:
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
- `with app.setup` imports
- required Prefect tasks defined inside the notebook
- flow entrypoint with `on_failure=[notify_on_failure]`
- edit-mode controls for config path, environment, dry-run, and parsed preview
- script-mode execution using the repo-local default config path

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add notebooks/ir/ir_webchanges_monitor.py tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py
git commit -m "feat: add ir monitor notebook flow"
```

### Task 11: Register deployment and update docs

**Files:**
- Modify: `prefect.yaml`
- Modify: `README.md`
- Modify: `docs/ADDING_FLOWS.md`
- Create: `tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_prefect_yaml_contains_ir_monitor_deployment():
    prefect_yaml = Path("prefect.yaml").read_text(encoding="utf-8")
    assert "ir-webchanges-monitor-prod" in prefect_yaml
    assert "notebooks/ir/ir_webchanges_monitor.py:run_ir_webchanges_monitor" in prefect_yaml
    assert "hourly_weekday_tokyo" in prefect_yaml
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py -v`
Expected: FAIL because the deployment and docs are not updated yet.

**Step 3: Write minimal implementation**

Add:
- a production deployment in `prefect.yaml`
- README setup notes for pinned `webchanges`, optional browser support, and Windows UTF-8 expectations
- a short flow-adding reference in `docs/ADDING_FLOWS.md` for the new IR notebook category

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add prefect.yaml README.md docs/ADDING_FLOWS.md tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py
git commit -m "docs: register ir monitor deployment and usage"
```

### Task 12: Run full verification before closing the branch

**Files:**
- Verify only: `pyproject.toml`
- Verify only: `src/services/ir_monitor/`
- Verify only: `scripts/ir_monitor/`
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

Run: `uv run ruff check src/services/ir_monitor scripts/ir_monitor notebooks/ir/ir_webchanges_monitor.py tests/unit/ir_monitor`
Expected: PASS

**Step 4: Run notebook validation**

Run: `uv run marimo check notebooks/ir/ir_webchanges_monitor.py`
Expected: PASS

**Step 5: Fix any issues found**

If linting or tests revealed issues during Steps 1-4, fix them and commit the fixes only. Do not re-commit work already committed in Tasks 1-11.

## Notes for the implementing engineer

- Use `docs/specs/prefect_webchanges.md` as the design source of truth.
- Keep the flow notebook thin; push reusable logic into `src/services/ir_monitor/`.
- Treat `company_id`, `page_label`, `target_kind`, and `user_visible_url` as required schema, not optional nice-to-haves.
- Normalized lines must start with `ITEM_KEY=` and must be deterministically sorted.
- Baseline initialization is a first-class status and must not trigger content notifications.
- Prefer the structured changed-jobs sidecar over stdout parsing whenever it exists.
- Group artifacts and notifications by company first, then by target/page.
- Do not add live website tests.
- Do not introduce `sys.path` mutations.
- Use `sys.executable` when generating webchanges execute filters so the active environment is explicit.

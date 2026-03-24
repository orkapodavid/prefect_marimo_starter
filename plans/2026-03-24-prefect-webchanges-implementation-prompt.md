# Implementation Prompt

> Paste this entire file as your first message to a new Claude Code session (or any
> LLM coding agent) pointed at this repository. The agent will implement the feature,
> run every test, and update the plan with outcomes.

---

## Your assignment

You are implementing a new feature in the `prefect-marimo-workflows` repository. Your
job is to follow a pre-written implementation plan task by task using strict
test-driven development. You have three input documents:

| Document | Path | Role |
|----------|------|------|
| **Spec** | `docs/specs/prefect_webchanges.md` | Source of truth for *what* to build. When the plan contradicts the spec, the spec wins. |
| **Plan** | `plans/2026-03-24-prefect-webchanges-implementation-plan.md` | Source of truth for *how* to build it. Follow it task by task. |
| **Master program** | `plans/2026-03-24-prefect-webchanges-master-program.md` | Your operating protocol. Defines the TDD loop, error recovery, and plan update rules. |

Read all three documents before writing any code.

---

## Repo context you need to know

These facts will save you from having to discover them. Verify each one during
bootstrap, but do not spend time re-exploring if they match.

### Package management

- **Manager:** `uv` (not pip, not poetry)
- **Install:** `uv sync --extra dev && uv pip install -e .`
- **Run:** prefix all commands with `uv run` (e.g., `uv run pytest ...`)
- **Python:** `>=3.12`

### Package layout

```
src/
  shared_utils/     # shared config, notifications
  services/         # feature packages (asx_scraper, tdnet, mssql, ir_monitor)
```

`pyproject.toml` maps `src/` as the package root via:
```toml
[tool.setuptools.packages.find]
where = ["src"]
```

The editable install (`uv pip install -e .`) makes `services.*` and `shared_utils.*`
importable as top-level packages.

### Import conventions

| Context | Example import | Note |
|---------|---------------|------|
| **Tests** (`tests/`) | `from src.services.ir_monitor.ir_monitor_models import MonitorConfig` | Use `src.` prefix |
| **Production code** (`src/`) | `from services.ir_monitor.ir_monitor_models import MonitorConfig` | No `src.` prefix |
| **Notebooks** (`notebooks/`) | `from shared_utils.config import get_settings` | No `src.` prefix |

The plan's test code already uses the correct `src.` prefix. If you see a test import
without it, that is a bug in the plan — add the prefix.

### Test configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- Runner: `pytest`
- Linter: `ruff`
- Fixtures: `tests/fixtures/ir_monitor/` (new for this feature)
- Existing fixture dirs: `tests/inputs/`, `tests/outputs/` (do not use these)

### Notebook pattern (Marimo)

Every notebook follows this structure — study `notebooks/maintenance/maintenance_pg_backup.py`
as a reference:

```python
# PEP 723 dependency block at top
import marimo
app = marimo.App(width="medium")

with app.setup:
    from prefect import task, flow
    from shared_utils.config import get_settings
    from shared_utils.prefect_notifications import notify_on_failure
    # ...

@app.function
@task(retries=2, retry_delay_seconds=30)
def some_task(...):
    ...

@app.function
@flow(name="flow-name", log_prints=True, on_failure=[notify_on_failure])
def main_flow(...):
    ...

@app.cell
def _(mo):
    # edit-mode UI controls (gated by mo.app_meta().mode == "edit")
    ...

@app.cell
def _(mo, main_flow):
    # script-mode execution (gated by mo.app_meta().mode == "script")
    ...

if __name__ == "__main__":
    app.run()
```

### Deployment pattern (prefect.yaml)

All deployments use YAML anchors:
```yaml
definitions:
  work_pools:
    windows_pool: &windows_pool
      name: windows-process-pool
      work_queue_name: default
  schedules:
    daily_6am: &daily_6am
      cron: "0 6 * * *"
      timezone: "Asia/Hong_Kong"
```

This feature adds a new anchor `hourly_weekday_tokyo` with `cron: "0 * * * 1-5"` and
`timezone: "Asia/Tokyo"`.

### Settings pattern (src/shared_utils/config.py)

Uses `pydantic_settings.BaseSettings` with `@lru_cache` via `get_settings()`. New
fields follow the `section_field_name` naming convention (e.g., `pg_backup_host`,
`ir_monitor_workspace_dir`).

### Existing service packages to study

- `src/services/tdnet/` — closest pattern to the new `ir_monitor` package
- `src/services/asx_scraper/` — good example of models, parsing, `__init__.py` exports

---

## Execution order

### Phase 1: Bootstrap

1. Read all three input documents (`spec`, `plan`, `master program`).
2. Run `uv sync --extra dev && uv pip install -e .`
3. Run `uv run pytest tests/ -v --tb=short` to establish a green baseline.
4. Run `uv run ruff check src/ tests/` to confirm zero lint issues.
5. Create branch: `git checkout -b feat/ir-webchanges-monitor`

**Gate:** Do not proceed if the baseline is red.

### Phase 2: Implement tasks 1–11

For each task in the plan (Tasks 1 through 11), execute the TDD cycle defined in
`plans/2026-03-24-prefect-webchanges-master-program.md` Section 3:

```
READ task → WRITE failing test → RUN (expect FAIL) → WRITE implementation →
RUN (expect PASS) → RUN regressions → RUN linter → COMMIT → LOG outcome
```

Critical rules:
- **One task, one commit.** Do not batch.
- **Test first.** Never write implementation before the failing test exists and runs.
- **Do not modify tests to pass.** Fix the implementation. The test is the contract.
- **Commit with the exact message from the plan.**
- **After each task, run `uv run pytest tests/unit/ir_monitor/ -v`** to catch regressions early.

When you encounter ambiguity:
- Check the spec first — it is the source of truth.
- Check the webchanges docs via Context7 MCP (`resolve-library-id` → `query-docs`) if
  you need to understand webchanges output format, job YAML schema, or config options.
- If still unclear, make a reasonable choice, document it in the plan with a
  `> **Actual:**` annotation, and move on.

### Phase 3: Verify (Task 12)

Run the full verification protocol from the plan's Task 12:

```bash
uv run pytest tests/unit/ir_monitor -v
uv run pytest tests/unit/test_config.py tests/unit/test_prefect_notifications.py -v
uv run ruff check src/services/ir_monitor scripts/ir_monitor notebooks/ir/ir_webchanges_monitor.py tests/unit/ir_monitor
uv run marimo check notebooks/ir/ir_webchanges_monitor.py
```

Fix any issues with separate `fix:` commits.

### Phase 4: Update the plan

After all tasks are complete:

1. Add a `> **Actual:**` annotation under any step where you deviated from the plan.
2. Add a final status block at the top of the plan file:

```markdown
> **Status:** COMPLETE | PARTIAL | BLOCKED
> **Completed:** YYYY-MM-DD
> **Total tasks:** 12
> **Tasks completed:** N
> **Deviations:** N (documented inline)
> **Test count:** N tests, all passing
> **Blocking issues:** (if any)
```

3. Commit the updated plan:
```bash
git add plans/2026-03-24-prefect-webchanges-implementation-plan.md
git commit -m "docs: update implementation plan with outcomes"
```

---

## What success looks like

When you are done, the repo should have:

- [ ] `pyproject.toml` — `webchanges` pinned as a dependency
- [ ] `src/shared_utils/config.py` — new `ir_monitor_*` settings fields
- [ ] `src/services/ir_monitor/` — full service package (models, config loader, dates,
      urls, normalizers, jobs builder, runner, report parser, artifacts, notifier)
- [ ] `src/services/ir_monitor/normalizers/` — JP, EN, JSON normalizers
- [ ] `scripts/ir_monitor/ir_monitor_normalize_content.py` — bridge script
- [ ] `config/ir_monitor/ir_monitor_targets.example.yaml` — example config
- [ ] `notebooks/ir/ir_webchanges_monitor.py` — Marimo notebook with Prefect flow
- [ ] `prefect.yaml` — `ir-webchanges-monitor-prod` deployment
- [ ] `tests/unit/ir_monitor/` — all unit tests passing
- [ ] `tests/fixtures/ir_monitor/` — HTML, JSON, PDF, and report fixtures
- [ ] `README.md` and `docs/ADDING_FLOWS.md` — updated with IR monitor docs
- [ ] Implementation plan — updated with final status and deviations
- [ ] 12+ commits on `feat/ir-webchanges-monitor` branch, one per task
- [ ] Zero ruff issues, zero test failures

---

## Error recovery quick reference

| Situation | Action |
|-----------|--------|
| Test fails for unexpected reason | Check import paths first. Tests use `src.` prefix. |
| Can't import a module in test | Verify `uv pip install -e .` was run. Check `__init__.py` exists. |
| Fixture file not found | Create it before running the test. Match test assertions. |
| webchanges behavior unclear | Use Context7 MCP to fetch webchanges docs. |
| Plan contradicts spec | Follow the spec. Update the plan with `> **Actual:**` annotation. |
| Linter fails | Fix the code. Never disable ruff rules. |
| Prior task's implementation is wrong | Fix it, re-run all tests, commit the fix separately. |
| Task 7 needs `pytest-mock` | Add `pytest-mock` to dev dependencies if not already present. |

---

## Start now

Begin with Phase 1: Bootstrap. Read the three input documents, establish the baseline,
create the branch, then start Task 1.

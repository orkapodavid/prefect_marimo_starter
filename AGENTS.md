# AGENTS.md - AI Coding Assistant Context

## Project Overview

This repository contains unified Prefect + Marimo notebooks where each notebook is BOTH:
- An interactive development environment (marimo edit mode)
- A production Prefect flow (script mode / Prefect deployment)

**Key architectural decision**: Flows and tasks are defined INSIDE marimo notebooks using decorator stacking, NOT in separate wrapper files.

---

## Core Pattern: Unified Notebooks

### Decorator Stacking (CRITICAL)

Always use `@app.function` FIRST, then the Prefect decorator:

```python
# ✅ CORRECT - @app.function wraps @task/@flow
@app.function
@task(retries=2, retry_delay_seconds=30)
def extract_data(source: str) -> pl.DataFrame:
    ...

@app.function
@flow(name="my-pipeline", log_prints=True)
def run_pipeline():
    ...

# ❌ WRONG - Prefect decorator first
@task
@app.function
def bad_task():
    ...
```

### Mode-Conditional Execution

Use `mo.app_meta().mode` to separate interactive development from production:

```python
@app.cell
def _(mo):
    if mo.app_meta().mode == "edit":
        # Interactive widgets, charts, debugging
        # This code ONLY runs in `marimo edit`
        pass

@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        # Production execution
        # This code runs via `python notebook.py` or Prefect worker
        run_pipeline()
```

### Shared Imports Pattern

Use `app.setup` block for imports shared across `@app.function` exports:

```python
with app.setup:
    from prefect import task, flow
    from prefect.blocks.system import Secret
    import polars as pl
    from pathlib import Path
```

---

## File Structure

```
notebooks/                    # All workflows live here (NOT in flows/)
├── etl/
│   ├── daily_sync.py        # Each notebook IS a Prefect flow
│   └── weekly_agg.py
├── reports/
│   └── daily_summary.py
src/
└── shared_utils/             # Shared Python utilities (non-flow code)
    ├── config.py
    └── database.py
prefect.yaml                  # Deployments point directly to notebooks
```

---

## Notebook Template

When creating a new notebook, use this template:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "polars>=1.0.0",
#     "prefect>=3.0.0",
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup:
    from prefect import task, flow
    import polars as pl

# ============================================================
# TASKS
# ============================================================

@app.function
@task(retries=2, retry_delay_seconds=30)
def extract(source: str) -> pl.DataFrame:
    """Extract data from source."""
    print(f"Extracting from {source}")
    return pl.read_parquet(source)

@app.function
@task
def transform(df: pl.DataFrame) -> pl.DataFrame:
    """Transform data."""
    return df.filter(pl.col("value") > 0)

@app.function
@task
def load(df: pl.DataFrame, dest: str):
    """Load to destination."""
    df.write_parquet(dest)

# ============================================================
# FLOW
# ============================================================

@app.function
@flow(name="etl-pipeline", log_prints=True)
def run_pipeline(source: str, dest: str) -> dict:
    """Main ETL pipeline."""
    df = extract(source)
    df = transform(df)
    load(df, dest)
    return {"rows": len(df)}

# ============================================================
# INTERACTIVE CELLS (edit mode only)
# ============================================================

@app.cell
def _():
    import marimo as mo
    return (mo,)

@app.cell
def _(mo):
    if mo.app_meta().mode == "edit":
        # Add widgets, charts here
        pass
    return

# ============================================================
# SCRIPT EXECUTION (production)
# ============================================================

@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        run_pipeline(
            source="data/input.parquet",
            dest="data/output.parquet"
        )
    return

if __name__ == "__main__":
    app.run()
```

---

## prefect.yaml Deployments

Deployments point directly to notebook flows:

```yaml
deployments:
  - name: etl-pipeline-prod
    entrypoint: notebooks/etl/daily_sync.py:run_pipeline
    parameters:
      source: "//server/data/input.parquet"
      dest: "//server/data/output.parquet"
    work_pool:
      name: windows-process-pool
    schedules:
      - cron: "0 6 * * *"
        timezone: "Asia/Hong_Kong"
```

---

## Common Patterns

### 1. Parameterized Flows

```python
@app.function
@flow(name="configurable-etl", log_prints=True)
def run_pipeline(
    source: str = "data/input.parquet",
    dest: str = "data/output.parquet",
    batch_size: int = 1000,
    environment: str = "dev"
) -> dict:
    """Parameters can be overridden in prefect.yaml or at runtime."""
    ...
```

### 2. Using Prefect Blocks for Secrets

```python
@app.function
@task
def connect_database():
    from prefect.blocks.system import Secret
    db_url = Secret.load("database-url").get()
    return create_engine(db_url)
```

### 3. Chaining Tasks with .pipe()

```python
@app.function
@flow(name="piped-etl", log_prints=True)
def run_pipeline():
    result = (
        extract("data/input.parquet")
        .pipe(validate)
        .pipe(transform)
        .pipe(enrich)
    )
    load(result, "data/output.parquet")
```

### 4. Interactive Widgets for Development

```python
@app.cell
def _(mo):
    if mo.app_meta().mode == "edit":
        source_input = mo.ui.text(value="data/sample.parquet", label="Source")
        run_btn = mo.ui.run_button(label="Test Pipeline")
        mo.vstack([source_input, run_btn])
    return

@app.cell  
def _(mo, source_input, run_btn):
    if mo.app_meta().mode == "edit" and run_btn.value:
        # Test individual tasks
        df = extract(source_input.value)
        df.head(10)
    return
```

---

## Execution Modes Reference

| Mode | Command | Use Case |
|------|---------|----------|
| Edit | `marimo edit notebook.py` | Interactive development |
| App | `marimo run notebook.py` | Read-only dashboard |
| Script | `python notebook.py` | CLI execution |
| Prefect | Via deployment | Scheduled/orchestrated |

---

## Anti-Patterns to Avoid

### ❌ DON'T: Separate flows/ and notebooks/ directories
```
# WRONG architecture
flows/
  etl_flow.py        # Thin wrapper
notebooks/
  etl_notebook.py    # Actual logic
```

### ❌ DON'T: Use MarimoNotebookRunner utility
```python
# WRONG - unnecessary complexity
from utils.marimo_runner import MarimoNotebookRunner
runner = MarimoNotebookRunner()
result = runner.run_notebook("notebooks/etl.py")
```

### ❌ DON'T: Wrong decorator order
```python
# WRONG - @task must come AFTER @app.function
@task
@app.function
def my_task():
    ...
```

### ✅ DO: Unified notebook with stacked decorators
```python
# CORRECT - single file, stacked decorators
@app.function
@task
def my_task():
    ...
```

---

## Testing Notebooks

```python
# tests/test_notebooks.py
def test_flow_importable():
    from notebooks.etl.daily_sync import run_pipeline
    assert callable(run_pipeline)
    assert hasattr(run_pipeline, "fn")  # Prefect flow attribute

def test_notebook_syntax(notebook_path):
    import subprocess
    result = subprocess.run(
        ["marimo", "check", str(notebook_path)],
        capture_output=True
    )
    assert result.returncode == 0
```

---

## Windows Deployment Notes

- Worker type: Process (spawns local Python processes)
- No Docker/Kubernetes required
- Use NSSM for Windows services
- IIS reverse proxy for authentication (external)
- SQLite for dev, PostgreSQL for production

---

## Quick Reference

| Task | Command |
|------|---------|
| Edit notebook | `marimo edit notebooks/etl/daily_sync.py` |
| Run as script | `python notebooks/etl/daily_sync.py` |
| Deploy all | `prefect deploy --all` |
| Start worker | `prefect worker start --pool windows-process-pool --type process` |
| Validate | `marimo check notebooks/` |

---

## LLM Instructions

When generating code for this project:

1. **Always use `@app.function` + `@task/@flow` stacking** in that order
2. **Put flow logic inside notebooks**, not in separate wrapper files
3. **Use `mo.app_meta().mode`** to separate edit/script behavior
4. **Include PEP 723 inline dependencies** at the top of notebooks
5. **Follow the template structure** for consistency
6. **Point prefect.yaml directly to notebook functions**
7. **Important: Environment Activation**
   - Before running any scripts, ensure the environment is activated.
   - Use `source .venv/bin/activate` or prefix commands with `uv run` if available.
   - If `uv` is missing, try using `python3 -m pip` instead of `pip`.
8. **Import Strategy (CRITICAL)**
   - **NEVER** use `sys.path.append("../../../")` for imports.
   - Project modules should be importable as installed packages (e.g., `from services.my_service import ...`).
   - Ensure the project is installed in editable mode (`pip install -e .`) or the `PYTHONPATH` includes the source root.
   - For notebooks, rely on the active environment where the project is installed.

---

## Model Context Protocol (MCP)

This repository is designed to work with **MCP servers** for Marimo and Prefect to provide enhanced context to AI assistants.

- **Marimo MCP**: Provides access to notebook state, active cells, and runtime variables.
- **Prefect MCP**: Uses the `prefect` CLI to fetch deployment status, flow runs, and logs.

Ensure your AI assistant (e.g., in Cursor or Claude Desktop) has these MCP servers configured for the best experience.

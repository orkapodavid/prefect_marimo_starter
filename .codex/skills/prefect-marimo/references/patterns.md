# Prefect-Marimo Patterns

This document provides complete notebook templates, advanced decorator stacking patterns, mode-conditional execution examples, anti-patterns to avoid, and integration with the project structure.

## Complete Notebook Template

Use this template when creating a new Prefect + Marimo unified notebook:

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

# ============================================================
# SHARED IMPORTS
# ============================================================

with app.setup:
    from prefect import task, flow
    from prefect.blocks.system import Secret
    import polars as pl
    from pathlib import Path

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
    print(f"Loaded {len(df)} rows to {dest}")

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
        # Input widgets for testing
        source_input = mo.ui.text(
            value="data/sample.parquet",
            label="Source Path"
        )
        dest_input = mo.ui.text(
            value="data/output.parquet",
            label="Destination Path"
        )
        run_btn = mo.ui.run_button(label="Test Pipeline")
        
        mo.vstack([source_input, dest_input, run_btn])
    return

@app.cell
def _(mo, source_input, dest_input, run_btn):
    if mo.app_meta().mode == "edit" and run_btn.value:
        # Test execution with widget inputs
        result = run_pipeline(
            source=source_input.value,
            dest=dest_input.value
        )
        mo.md(f"**Pipeline completed:** {result}")
    return

# ============================================================
# SCRIPT EXECUTION (production)
# ============================================================

@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        # Production execution
        run_pipeline(
            source="data/input.parquet",
            dest="data/output.parquet"
        )
    return

if __name__ == "__main__":
    app.run()
```

## Advanced Decorator Stacking Patterns

### With Custom Cache Keys

```python
from prefect.tasks import task_input_hash
from datetime import timedelta

@app.function
@task(
    retries=3,
    retry_delay_seconds=30,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1)
)
def cached_extraction(source: str) -> pl.DataFrame:
    """Expensive extraction with caching."""
    print(f"Actually extracting from {source}")
    return pl.read_parquet(source)
```

### With Dynamic Task Names

```python
@app.function
@task(task_run_name="process-{item_id}")
def process_item(item_id: str) -> dict:
    """Process individual item with dynamic name."""
    return {"item_id": item_id, "status": "processed"}

@app.function
@flow(name="batch-processor", log_prints=True)
def batch_flow(item_ids: list[str]) -> list[dict]:
    """Process multiple items."""
    results = []
    for item_id in item_ids:
        result = process_item(item_id)
        results.append(result)
    return results
```

### With Prefect Blocks

```python
@app.function
@task
def connect_database():
    """Connect using credentials from Prefect blocks."""
    from prefect.blocks.system import Secret
    
    db_url = Secret.load("database-url").get()
    username = Secret.load("db-username").get()
    password = Secret.load("db-password").get()
    
    return create_connection(db_url, username, password)

@app.function
@flow(name="secure-etl", log_prints=True)
def secure_pipeline():
    """Pipeline using secure credentials."""
    conn = connect_database()
    data = extract_from_db(conn)
    return process_data(data)
```

### With Task Mapping

```python
@app.function
@task(retries=2)
def process_file(filepath: str) -> dict:
    """Process single file."""
    df = pl.read_csv(filepath)
    return {"file": filepath, "rows": len(df)}

@app.function
@flow(name="batch-file-processor", log_prints=True)
def process_files(filepaths: list[str]) -> list[dict]:
    """Process multiple files in parallel."""
    # Use .map() for parallel execution
    results = process_file.map(filepaths)
    return results
```

## Mode-Conditional Execution Examples

### Interactive Development Mode

```python
@app.cell
def _(mo):
    if mo.app_meta().mode == "edit":
        # Create interactive development UI
        mo.md("""
        # ETL Pipeline Development
        
        Test the pipeline with sample data below.
        """)
    return

@app.cell
def _(mo):
    if mo.app_meta().mode == "edit":
        # File browser for source selection
        source_selector = mo.ui.dropdown(
            options=[
                "data/sample_small.parquet",
                "data/sample_medium.parquet",
                "data/sample_large.parquet"
            ],
            label="Select test data"
        )
        
        # Toggle for dry-run mode
        dry_run = mo.ui.checkbox(
            value=True,
            label="Dry run (don't write output)"
        )
        
        mo.vstack([source_selector, dry_run])
    return

@app.cell
def _(mo, source_selector, dry_run):
    if mo.app_meta().mode == "edit":
        # Preview data
        df = extract(source_selector.value)
        mo.ui.table(df.head(100))
    return

@app.cell
def _(mo, source_selector, dry_run, run_btn):
    if mo.app_meta().mode == "edit" and run_btn.value:
        # Execute with interactive parameters
        if dry_run.value:
            # Just preview transformation
            df = extract(source_selector.value)
            transformed = transform(df)
            mo.md(f"**Dry run complete:** {len(transformed)} rows ready")
        else:
            # Full execution
            result = run_pipeline(
                source=source_selector.value,
                dest="data/test_output.parquet"
            )
            mo.md(f"**Pipeline complete:** {result}")
    return
```

### Script/Production Mode

```python
@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        # Production execution with environment-based config
        import os
        
        environment = os.getenv("ENVIRONMENT", "dev")
        
        if environment == "prod":
            source = "//server/prod/data/input.parquet"
            dest = "//server/prod/data/output.parquet"
        else:
            source = "data/dev/input.parquet"
            dest = "data/dev/output.parquet"
        
        # Execute pipeline
        result = run_pipeline(source=source, dest=dest)
        print(f"Pipeline completed: {result}")
    return
```

### App Mode (Read-Only Dashboard)

```python
@app.cell
def _(mo):
    if mo.app_meta().mode == "run":
        # Display dashboard UI
        mo.md("# ETL Pipeline Dashboard")
    return

@app.cell
def _(mo):
    if mo.app_meta().mode == "run":
        # Refresh button for dashboard
        refresh = mo.ui.run_button(label="Refresh Data")
        refresh
    return

@app.cell
def _(mo, refresh):
    if mo.app_meta().mode == "run":
        # Load and display latest results
        latest_output = pl.read_parquet("data/output.parquet")
        
        mo.vstack([
            mo.md(f"**Total Rows:** {len(latest_output)}"),
            mo.ui.table(latest_output, page_size=20)
        ])
    return
```

## Common Anti-Patterns to Avoid

### ❌ Wrong Decorator Order

```python
# WRONG - Prefect decorator first
@task(retries=2)
@app.function
def bad_task():
    pass

# CORRECT
@app.function
@task(retries=2)
def good_task():
    pass
```

**Why**: `@app.function` must wrap the Prefect decorator to properly export the function for external use.

### ❌ Separate Wrapper Files

```python
# WRONG - separate flows/etl_wrapper.py
from notebooks.etl import notebook_function

@flow
def wrapper_flow():
    return notebook_function()

# CORRECT - everything in the notebook
@app.function
@flow(name="etl-pipeline")
def etl_flow():
    # All logic here
    pass
```

**Why**: Violates the unified architecture principle. Keep everything in one place.

### ❌ Missing Mode Guards

```python
# WRONG - widget code runs in production
@app.cell
def _(mo):
    # This runs in ALL modes!
    widget = mo.ui.slider(0, 100)
    widget
    return

# CORRECT - use mode detection
@app.cell
def _(mo):
    if mo.app_meta().mode == "edit":
        widget = mo.ui.slider(0, 100)
        widget
    return
```

**Why**: Interactive widgets should not run in production script mode.

### ❌ Hardcoded Paths

```python
# WRONG - hardcoded production paths
@app.function
@flow
def bad_flow():
    df = extract("//prod-server/data/input.parquet")
    return df

# CORRECT - parameterized paths
@app.function
@flow
def good_flow(source: str = "data/input.parquet"):
    df = extract(source)
    return df
```

**Why**: Parameterization enables testing, different environments, and deployment flexibility.

### ❌ Missing PEP 723 Dependencies

```python
# WRONG - no dependencies specified
import marimo
app = marimo.App()

# CORRECT - dependencies at top
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "prefect>=3.0.0",
#     "polars>=1.0.0",
# ]
# ///

import marimo
app = marimo.App()
```

**Why**: Makes notebook self-contained and reproducible.

## Project Integration

### Integration with notebooks/ Directory

Place notebooks in the appropriate subdirectory:

```
notebooks/
├── etl/
│   ├── daily_sync.py          # Daily data synchronization
│   └── weekly_agg.py           # Weekly aggregation
├── reports/
│   ├── daily_summary.py        # Daily summary report
│   └── weekly_metrics.py       # Weekly metrics
└── examples/
    └── tutorial.py             # Example notebook
```

### Integration with src/ Utilities

Import shared utilities from `src/` in notebooks:

```python
with app.setup:
    from prefect import task, flow
    import polars as pl
    
    # Import project utilities
    from services.mssql import MSSQLService
    from shared_utils.config import get_config

@app.function
@task
def extract_from_database():
    """Extract data using shared service."""
    config = get_config()
    service = MSSQLService(
        server=config.db_host,
        database=config.db_name
    )
    return service.execute_query("SELECT * FROM customers")
```

### Integration with prefect.yaml

```yaml
name: prefect-marimo-project
prefect-version: "3.0"

deployments:
  # ETL deployments
  - name: daily-sync-prod
    entrypoint: notebooks/etl/daily_sync.py:run_pipeline
    work_pool:
      name: windows-process-pool
    parameters:
      source: "//server/data/input.parquet"
      dest: "//server/data/output.parquet"
      environment: "prod"
    schedules:
      - cron: "0 6 * * *"
        timezone: "Asia/Hong_Kong"
  
  # Report deployments
  - name: daily-summary-prod
    entrypoint: notebooks/reports/daily_summary.py:generate_report
    work_pool:
      name: windows-process-pool
    parameters:
      report_date: "{{ prefect.runtime.scheduled_start_time }}"
    schedules:
      - cron: "0 8 * * *"
        timezone: "Asia/Hong_Kong"
```

### Testing Integration

While notebooks are manually tested via `marimo edit`, shared utilities should have unit tests:

```python
# tests/unit/test_notebook_utils.py
import pytest
from notebooks.etl.daily_sync import extract, transform

def test_extract():
    """Test extraction logic."""
    # Mock or use test data
    result = extract("test_data.parquet")
    assert len(result) > 0

def test_transform():
    """Test transformation logic."""
    import polars as pl
    test_df = pl.DataFrame({"value": [1, -1, 2, -2]})
    result = transform(test_df)
    assert len(result) == 2  # Only positive values
```

## Best Practices Summary

1. **Always use `@app.function` before `@task/@flow`**
2. **Use mode detection for interactive vs. production code**
3. **Parameterize flows for flexibility**
4. **Include PEP 723 dependencies**
5. **Keep all logic in notebooks** (no wrapper files)
6. **Use shared utilities from `src/` for reusable code**
7. **Point `prefect.yaml` directly to notebook functions**
8. **Test interactively with `marimo edit`**
9. **Deploy with `prefect deploy --all`**
10. **Monitor execution via Prefect UI**

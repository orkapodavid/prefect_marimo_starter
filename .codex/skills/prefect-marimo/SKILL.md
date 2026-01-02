---
name: Prefect-Marimo
description: This skill should be used when the user asks to "create a prefect marimo notebook", "combine prefect with marimo", "deploy marimo as prefect flow", "stack decorators", "use mode-conditional execution", or mentions unified Prefect-Marimo architecture, @app.function with @flow/@task decorators.
version: 0.1.0
---

# Prefect-Marimo

This skill provides guidance for the unified Prefect + Marimo notebook architecture where each notebook is both an interactive development environment and a production Prefect flow.

## Architecture Overview

Marimo notebooks contain Prefect flows and tasks directly, eliminating the need for separate wrapper files. This unified approach enables:

- **Interactive Development**: Use `marimo edit` to develop flows with widgets, charts, and live data exploration
- **Production Execution**: Deploy the same notebook as a Prefect flow via `prefect.yaml`
- **No Code Duplication**: Single source of truth for both development and production
- **Mode-Conditional Logic**: Separate interactive and production code paths using `mo.app_meta().mode`

**Key Principle**: Flows and tasks are defined INSIDE marimo notebooks using decorator stacking, NOT in separate wrapper files.

## Core Pattern

### Decorator Stacking (CRITICAL)

Always use `@app.function` FIRST, then the Prefect decorator:

```python
# ✅ CORRECT - @app.function wraps @task/@flow
@app.function
@task(retries=2, retry_delay_seconds=30)
def extract_data(source: str) -> pl.DataFrame:
    return pl.read_parquet(source)

@app.function
@flow(name="my-pipeline", log_prints=True)
def run_pipeline(source: str) -> dict:
    df = extract_data(source)
    return {"rows": len(df)}

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
        run_pipeline(source="data/input.parquet")
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

## Deployment

Point `prefect.yaml` deployments directly to notebook flows:

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

**Key Points**:
- `entrypoint` points directly to the notebook file and flow function
- Parameters can be overridden in the deployment configuration
- Notebooks execute in script mode when triggered by Prefect

## Key Rules

1. **Decorator Order**: `@app.function` ALWAYS comes before `@task` or `@flow`
2. **Mode Detection**: Use `mo.app_meta().mode` to separate edit/script behavior
3. **Single Source**: Put ALL flow logic in notebooks, not wrapper files
4. **PEP 723 Dependencies**: Include inline dependencies in notebook header
5. **Direct Entrypoint**: Point `prefect.yaml` directly to `notebook.py:function`

## Additional Resources

### Reference Files

For complete templates and advanced patterns, consult:
- **`references/patterns.md`** - Complete notebook template, advanced decorator stacking, mode-conditional examples, anti-patterns, and project integration details
---
name: Prefect-Marimo
description: This skill should be used when the user asks to "create a prefect marimo notebook", "combine prefect with marimo", "deploy marimo as prefect flow", "stack decorators", "use mode-conditional execution", or mentions unified Prefect-Marimo architecture, @app.function with @flow/@task decorators.
version: 0.1.0
---

# Prefect-Marimo

This skill provides guidance for the unified Prefect + Marimo notebook architecture where each notebook is both an interactive development environment and a production Prefect flow.

## Architecture Overview

Marimo notebooks contain Prefect flows and tasks directly, eliminating the need for separate wrapper files. This unified approach enables:

- **Interactive Development**: Use `marimo edit` to develop flows with widgets, charts, and live data exploration
- **Production Execution**: Deploy the same notebook as a Prefect flow via `prefect.yaml`
- **No Code Duplication**: Single source of truth for both development and production
- **Mode-Conditional Logic**: Separate interactive and production code paths using `mo.app_meta().mode`

**Key Principle**: Flows and tasks are defined INSIDE marimo notebooks using decorator stacking, NOT in separate wrapper files.

## Core Pattern

### Decorator Stacking (CRITICAL)

Always use `@app.function` FIRST, then the Prefect decorator:

```python
# ✅ CORRECT - @app.function wraps @task/@flow
@app.function
@task(retries=2, retry_delay_seconds=30)
def extract_data(source: str) -> pl.DataFrame:
    return pl.read_parquet(source)

@app.function
@flow(name="my-pipeline", log_prints=True)
def run_pipeline(source: str) -> dict:
    df = extract_data(source)
    return {"rows": len(df)}

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
        run_pipeline(source="data/input.parquet")
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

## Deployment

Point `prefect.yaml` deployments directly to notebook flows:

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

**Key Points**:
- `entrypoint` points directly to the notebook file and flow function
- Parameters can be overridden in the deployment configuration
- Notebooks execute in script mode when triggered by Prefect

## Key Rules

1. **Decorator Order**: `@app.function` ALWAYS comes before `@task` or `@flow`
2. **Mode Detection**: Use `mo.app_meta().mode` to separate edit/script behavior
3. **Single Source**: Put ALL flow logic in notebooks, not wrapper files
4. **PEP 723 Dependencies**: Include inline dependencies in notebook header
5. **Direct Entrypoint**: Point `prefect.yaml` directly to `notebook.py:function`

## Additional Resources

### Reference Files

For complete templates and advanced patterns, consult:
- **`references/patterns.md`** - Complete notebook template, advanced decorator stacking, mode-conditional examples, anti-patterns, and project integration details

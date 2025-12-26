# .codex/skills/prefect-marimo.md

## Prefect + Marimo Unified Skill

### Architecture

Marimo notebooks contain Prefect flows and tasks directly:
- No separate wrapper files
- Decorator stacking: `@app.function` + `@task/@flow`
- Mode-conditional execution via `mo.app_meta().mode`

### Core Pattern

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo", "prefect>=3.0.0", "polars"]
# ///

import marimo
app = marimo.App()

with app.setup:
    from prefect import task, flow
    import polars as pl

@app.function
@task(retries=2)
def extract(source: str) -> pl.DataFrame:
    return pl.read_parquet(source)

@app.function
@flow(name="my-pipeline", log_prints=True)
def run_pipeline(source: str) -> dict:
    df = extract(source)
    return {"rows": len(df)}

@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        run_pipeline("data/input.parquet")
    return

if __name__ == "__main__":
    app.run()
```

### Deployment

```yaml
# prefect.yaml
deployments:
  - name: pipeline-prod
    entrypoint: notebooks/etl/pipeline.py:run_pipeline
    work_pool:
      name: windows-process-pool
```

### Key Rules

1. `@app.function` ALWAYS comes before `@task` or `@flow`
2. Use `mo.app_meta().mode` to separate edit/script behavior
3. Put ALL flow logic in notebooks, not wrapper files
4. Include PEP 723 dependencies in notebook header
5. Point prefect.yaml directly to notebook:function

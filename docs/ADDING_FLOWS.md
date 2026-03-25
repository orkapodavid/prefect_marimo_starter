# Adding New Flows

This guide explains how to add new workflows using unified Prefect + Marimo notebooks.

## Step 1: Create a Notebook
1. Create a new `.py` file in `notebooks/` (e.g., `notebooks/reports/daily_summary.py`).
2. Open it with Marimo: `marimo edit notebooks/reports/daily_summary.py`.
3. Follow the template defined in `AGENTS.md`.

## Step 2: Define Tasks and Flow
Inside the notebook:
1. Use `@app.function` + `@task` for tasks.
2. Use `@app.function` + `@flow` for the main pipeline.
3. Use `mo.app_meta().mode` to separate interactive logic from flow execution.

Example:
```python
@app.function
@task
def extract():
    ...

@app.function
@flow(name="daily-report")
def run_pipeline():
    extract()
```

## Step 3: Add to prefect.yaml
Add a new deployment entry to `prefect.yaml`, pointing directly to the notebook function:
```yaml
deployments:
  - name: daily-report
    entrypoint: notebooks/reports/daily_summary.py:run_pipeline
    work_pool: *windows_pool
    schedule: *daily_7am
```

## Step 4: Deploy
Run `prefect deploy --name daily-report` to register the new flow.

For repo-local server and worker setup, see `docs/prefect/prefect_local_dev_stack.md`.

## IR Monitor Example

The IR monitor flow lives at `notebooks/ir/ir_webchanges_monitor.py`.

Use this pattern when the workflow needs:
1. A unified Marimo + Prefect notebook entrypoint.
2. Shared service code under `src/services/ir_monitor/`.
3. A direct deployment entry in `prefect.yaml`.
4. Config files under `config/ir_monitor/`.

## X Monitor Example

The X monitor flows live under `notebooks/x_monitor/`, with the polling entrypoint at
`notebooks/x_monitor/x_monitor_poll_accounts.py`.

Use this pattern when the workflow needs:
1. A unified Marimo + Prefect notebook entrypoint for each flow.
2. Shared service code under `src/services/x_monitor/`.
3. PostgreSQL-backed state plus Prefect deployments in `prefect.yaml`.
4. Config files under `config/x_monitor/`.

## Financial Monitor Example

The financial monitor flow lives at
`notebooks/financial_monitor/financial_monitor_daily_pipeline.py`.

Use this pattern when the workflow needs:
1. A unified Marimo + Prefect notebook entrypoint.
2. Shared service code under `src/services/financial_monitor/`.
3. TDnet discovery plus EDINET retrieval in one orchestration flow.
4. PostgreSQL-backed normalized persistence plus Prefect artifacts.
5. Config files under `config/financial_monitor/`.
6. A script-mode smoke path that reuses the same orchestration helper as the
   deployed flow, with divergence limited to input selection or explicit
   fallback execution mode.

# Adding New Flows

This guide explains how to add new workflows using Marimo notebooks and Prefect.

## Step 1: Create a Marimo Notebook
1. Create a new `.py` file in `notebooks/` (e.g., `notebooks/reports/daily_summary.py`).
2. Open it with Marimo: `marimo edit notebooks/reports/daily_summary.py`.
3. Follow the standard template:
   - Include a `@app.cell` for configuration.
   - Include a `@app.function` named `run(parameters)` as the entry point.

## Step 2: Create a Prefect Flow
1. Create a corresponding flow file in `flows/` (e.g., `flows/reporting_flow.py`).
2. Import the `MarimoNotebookRunner`.
3. Define a task that calls the notebook.
4. Define a flow that calls the task.

Example:
```python
from prefect import flow, task
from workflow_utils.marimo_runner import MarimoNotebookRunner

@task
def run_report():
    runner = MarimoNotebookRunner()
    return runner.run_notebook("notebooks/reports/daily_summary.py")

@flow(name="daily-report")
def daily_report_flow():
    run_report()
```

## Step 3: Add to prefect.yaml
Add a new deployment entry to `prefect.yaml`:
```yaml
deployments:
  - name: daily-report
    entrypoint: flows/reporting_flow.py:daily_report_flow
    work_pool: *windows_pool
    schedule: *daily_7am
```

## Step 4: Deploy
Run `prefect deploy --name daily-report` to register the new flow.

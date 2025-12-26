# Development Guide

This guide describes how to set up your local development environment.

## Prerequisites
- Python 3.11 or 3.12
- Git

## Setup

### Windows (PowerShell)
```powershell
.\scripts\local\setup-dev.ps1
.\venv\Scripts\Activate.ps1
```

### Mac/Linux
```bash
chmod +x scripts/local/setup-dev.sh
./scripts/local/setup-dev.sh
source venv/bin/activate
```

## Running Marimo
To edit an existing notebook:
```bash
marimo edit notebooks/etl/extract_data.py
```

To create a new notebook:
```bash
marimo edit notebooks/your_new_notebook.py
```

## Running Prefect
Start a local Prefect server for testing:
```bash
prefect server start
```

In a new terminal:
```bash
# Register deployments
prefect deploy --all

# Start a worker
prefect worker start --pool windows-process-pool
```

## Code Quality
We use `ruff` for linting and `marimo check` for notebook validation.
```bash
ruff check .
marimo check notebooks/
```

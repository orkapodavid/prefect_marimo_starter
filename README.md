# Prefect + Marimo Unified Workflows

Workflow orchestration using **Marimo notebooks** with embedded **Prefect flows**.

## Architecture

Each notebook is BOTH:
- 🎨 **Interactive development environment** (marimo edit mode)
- 🚀 **Production Prefect flow** (script mode)

```
┌─────────────────────────────────────────────────────┐
│           MARIMO NOTEBOOK (.py file)                │
│                                                     │
│  ┌─────────────────┐    ┌─────────────────────┐    │
│  │ @app.function   │    │ @app.cell           │    │
│  │ @task           │    │ if mode == "edit":  │    │
│  │ def extract()   │    │   # Interactive UI  │    │
│  └─────────────────┘    │   # Charts, widgets │    │
│                         └─────────────────────┘    │
│  ┌─────────────────┐    ┌─────────────────────┐    │
│  │ @app.function   │    │ @app.cell           │    │
│  │ @flow           │    │ if mode == "script":│    │
│  │ def run_pipe()  │    │   run_pipeline()    │    │
│  └─────────────────┘    └─────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

## Setup Guide

### 1. Renaming the Project
If you are using this as a template, rename the project in the following files:

1.  **`pyproject.toml`**: Update `name` and `description`.
2.  **`prefect.yaml`**: Update `name` (and optional `prefect-version` if needed).
3.  **Root Directory**: Rename the root folder to your project name.

### 2. Environment Setup

This project uses `uv` for fast package management.

**Mac/Linux:**
```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Activate environment
source .venv/bin/activate
```

**Windows:**
```powershell
# Install uv (if not installed)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Create virtual environment and install dependencies
uv sync

# Activate environment
.venv\Scripts\activate
```

### 3. Start Infrastructure

**Terminal 1: Prefect Server**
```bash
prefect server start
```

**Terminal 2: Prefect Worker**
```bash
# Starts a process worker that executes flows locally
prefect worker start --pool windows-process-pool --type process
```

### 4. Development Loop

1.  **Edit**: `marimo edit notebooks/etl/daily_sync.py`
2.  **Run**: `python notebooks/etl/daily_sync.py`
3.  **Deploy**: `prefect deploy --all`

## Running Modes

| Mode | Command | Use Case |
|------|---------|----------|
| **Edit** | `marimo edit notebook.py` | Interactive development |
| **App** | `marimo run notebook.py` | Read-only dashboard |
| **Script** | `python notebook.py` | CLI execution |
| **Prefect** | Via deployment | Scheduled/orchestrated |

## Testing

Tests are organized into the following directories:

*   `tests/unit`: Unit tests for individual components. These should be fast and not require external dependencies.
*   `tests/integration`: Integration tests that may involve multiple components or external systems (e.g., databases, APIs).
*   `tests/notebooks`: Interactive Marimo notebooks used for manual verification and exploration.

### Running Tests

We use `pytest` to run unit and integration tests.

- **Run all tests:** `pytest`
- **Run unit tests:** `pytest tests/unit`
- **Run integration tests:** `pytest tests/integration`

Notebook tests are interactive Marimo notebooks. You can run them to manually verify functionality.
- **Run notebook test:** `marimo edit tests/notebooks/<notebook_name>.py`

## AI Assistant Integration

This project is optimized for AI-assisted development (Cursor, Copilot, etc.). 

- **Context**: `AGENTS.md` and `.codex/skills/` provide architectural patterns.
- **MCP**: Supports **Marimo** and **Prefect** Model Context Protocol (MCP) servers for deeper IDE integration.

## Production Deployment (Windows Server)
This starter includes a comprehensive suite of scripts for deploying to air-gapped Windows Server 2019/2022 environments.

**Full Guide:** [`docs/Deploy_Prefect_Onto_Window_Server.md`](docs/Deploy_Prefect_Onto_Window_Server.md)

### Deployment Scripts (`scripts/windows/`)

1.  **Prepare Offline Assets** (Run on internet-connected machine):
    - Downloads Python, Wheels, NSSM, IIS Modules.
    - **Bundles the current project source code** into the offline package.
    ```powershell
    .\scripts\windows\01_download_offline_assets.ps1 -Destination "C:\PrefectOffline"
    ```
2.  **Transfer Package**:
    - Copy the **entire** `C:\PrefectOffline` folder to your air-gapped Windows Server.

3.  **Install Environment & Code** (Run on Target Server):
    - Installs Python, creates venv, and copies project code to `C:\PrefectServer`.
    ```powershell
    .\scripts\windows\02_install_server_env.ps1 -OfflineSource "C:\PrefectOffline"
    ```
4.  **Configure Services** (Run on Target Server):
    ```powershell
    .\scripts\windows\03_configure_services.ps1
    ```
4.  **Setup IIS Proxy** (Run on Target Server):
    ```powershell
    .\scripts\windows\04_setup_iis_proxy.ps1
    ```
5.  **Secure Firewall**:
    ```powershell
    .\scripts\windows\05_configure_firewall.ps1
    ```

## Adding a New Workflow


1. Create notebook: `notebooks/category/my_workflow.py`
2. Define tasks with `@app.function` + `@task`
3. Define flow with `@app.function` + `@flow`
4. Add interactive cells with `if mo.app_meta().mode == "edit":`
5. Add script execution with `if mo.app_meta().mode == "script":`
6. Add deployment to `prefect.yaml`
7. Deploy: `prefect deploy --name my-workflow-prod`

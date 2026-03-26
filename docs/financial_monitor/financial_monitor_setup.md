# Financial Monitor Setup

## Overview

The financial monitor runs from
`notebooks/financial_monitor/financial_monitor_daily_pipeline.py` and combines:

- TDnet discovery for configured Japanese disclosure targets
- EDINET document retrieval for matched issuers
- XBRL-first cash metric extraction
- deterministic liquidity and fundraising flagging
- PostgreSQL persistence into `tblFinancialMonitor*` tables

## Configuration

1. Copy the example config:

```bash
cp config/financial_monitor/financial_monitor_targets.example.yaml config/financial_monitor/financial_monitor_targets.yaml
```

2. Edit `config/financial_monitor/financial_monitor_targets.yaml` with your target companies.

3. For local runs, make sure you have a repo-root `.env` file. If you do not already
   have one, start from the example:

```bash
cp .env.example .env
```

Set `PROJECT_ROOT` in that file to this repo's absolute path on your machine.

4. Set the database URL if you do not want the default:

```bash
FINANCIAL_MONITOR_DATABASE_URL=postgresql://localhost:5432/workflow_app
```

If the flow will run inside the Dockerized Prefect worker and the database is on
your host machine, use `host.docker.internal` instead of `localhost`.

5. Repo-local Prefect development uses:

```bash
PREFECT_API_URL=http://127.0.0.1:4201/api
PROJECT_ROOT=/absolute/path/to/prefect_marimo_starter
PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://prefect:change-me@host.docker.internal:5432/prefect
PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH=prefect_marimo_starter,public
PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_APPLICATION_NAME=prefect-marimo-starter
```

## EDINET API Key

The workflow resolves the EDINET API key in this order:

1. Prefect Secret block `financial-monitor-edinet-api-key`
2. Environment variable `EDINET_API_KEY`
3. Fail fast with a configuration error

For standalone local execution outside Prefect flow/task run context, the
repo-root `.env` file is loaded as part of the environment-variable fallback
path. That file is gitignored, so it is the recommended local place to store
`EDINET_API_KEY` for notebook smoke checks and one-off local scripts.

For actual Prefect task/flow runs, keep the runtime order explicit:

1. Prefect Secret block `financial-monitor-edinet-api-key`
2. Environment variable `EDINET_API_KEY`
3. Fail fast

Example local `.env` entry:

```bash
EDINET_API_KEY=<your-edinet-key>
```

Create the Prefect Secret block if you want the repo-default resolution path:

```bash
prefect block register -m prefect.blocks.system
prefect block create secret financial-monitor-edinet-api-key --value "<your-edinet-key>"
```

## Local Execution

## Repo-local Prefect Server + Worker via Docker / OrbStack

This repo includes a `docker-compose.yaml` that runs both a local Prefect server
and a local Prefect process worker. Prefect server state is stored in PostgreSQL,
not in a repo-local SQLite database.

For the repo-level Prefect dev-stack reference, including recovery and
troubleshooting notes, see `docs/prefect/prefect_local_dev_stack.md`.

The worker bind-mounts the repo from the host path declared in `PROJECT_ROOT`,
but the container mounts that checkout into a fixed internal path and starts
from the repo root there. The flow code and config loaders resolve repo-relative
paths from the actual repo root, so the host path does not need to exist inside
the container. Docker-worker deployments use a deployment-level Prefect pull
step that points at that fixed internal worker path instead of a host-specific
absolute directory. Host-run deployments such as the macOS X monitor flows do
not use that Docker-only pull step.

If you want this Prefect server to share the same PostgreSQL database instance
as other Prefect servers or applications, give this repo a unique schema name in
`PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH`. Keep `public` in
the search path so PostgreSQL extensions such as `pg_trgm` remain available.

Start the dev stack:

```bash
docker compose up -d
```

Check service health/logs:

```bash
docker compose ps
docker compose logs -f prefect-server prefect-worker
```

Stop it:

```bash
docker compose down
```

The server listens on `http://127.0.0.1:4201`, which matches the repo-local
`.env` defaults. The worker automatically ensures the `windows-process-pool`
work pool exists, then starts polling it. The server startup also bootstraps the
repo-specific schema and `pg_trgm` extension in PostgreSQL before launching the
API.

The deployment default comes from `FINANCIAL_MONITOR_CONFIG_PATH` in `.env`,
which defaults to the tracked repo path:

- `config/financial_monitor/financial_monitor_targets.yaml`

That file is required for scheduled or non-dry-run deployment runs. If you want
to smoke-test with the example targets instead, pass an explicit `config_path`
override pointing at:

- `config/financial_monitor/financial_monitor_targets.example.yaml`

If a flow running inside the worker container needs to reach a database or
other service running directly on your Mac, do not leave that service URL at
`localhost`. Inside the container, point those URLs at `host.docker.internal`
instead.

Manual notebook smoke checks:

```bash
uv run python notebooks/financial_monitor/financial_monitor_daily_pipeline.py
uv run marimo edit notebooks/financial_monitor/financial_monitor_daily_pipeline.py
uv run marimo check notebooks/financial_monitor/financial_monitor_daily_pipeline.py
```

Script-mode behavior is intentionally small and explicit:

- If `config/financial_monitor/financial_monitor_targets.yaml` exists, the notebook
  runs the real decorated Prefect flow with `environment="prod"` and
  `dry_run=False`.
- If that tracked config is absent, the notebook falls back to
  `config/financial_monitor/financial_monitor_targets.example.yaml` with
  `environment="dev"` and `dry_run=True` so the repo always has a working local
  smoke path.
- Both paths reuse the same notebook orchestration sequence; the fallback path
  only changes the config input and invocation mode.

Path behavior:

- By default, durable workspace files go under
  `data/financial_monitor/<environment>/`.
- Reports go under `reports/financial_monitor/<environment>/`.
- If the config file sets `runtime.workspace_dir`, that explicit path wins over
  the environment-derived workspace default.

Artifact behavior:

- JSON and Markdown run summaries are always written to the report directory.
- Prefect Markdown artifact registration only happens when the notebook is
  running inside a real Prefect flow/task run context.
- Standalone script smoke checks still write repo-local summaries, but they do
  not try to publish a Prefect UI artifact.

## Prefect Deployment

The production deployment name is `financial-monitor-daily-prod` and uses
`windows-process-pool`.

Register the deployment:

```bash
uv run prefect deploy --name financial-monitor-daily-prod
```

The Docker Compose worker already runs:

```bash
prefect worker start --pool windows-process-pool --type process
```

Schedule details:

- Cron: `0 21 * * 1-5`
- Timezone: `Asia/Tokyo`

## Notes

- TDnet is used for announcement discovery, not for the primary numeric source.
- EDINET XBRL is the primary source for cash and cash-flow metrics in v1.
- EDINET document scoping stays narrow: only TDnet-matched, results-like targets
  with `include_edinet: true` are considered for EDINET intake.
- Temporary debugging files should stay under `tmp/financial_monitor/`.

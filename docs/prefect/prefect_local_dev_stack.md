# Prefect Local Dev Stack

## Overview

This repo includes a Docker Compose-based Prefect development stack for local
work:

- `prefect-server` serves the API and UI on `http://127.0.0.1:4201`
- `prefect-worker` starts a local process worker and ensures
  `windows-process-pool` exists

Repo-relative workflow paths are resolved from the actual repo root at runtime.
The Docker worker bind-mounts the host checkout into a fixed internal repo path,
and `prefect.yaml` now uses `set_working_directory` only for that fixed
container path, not for a host-specific absolute path.

The stack is defined in `docker-compose.yaml` and uses repo-local state under
your local PostgreSQL instance, not a repo-local SQLite database.

## Required `.env` Settings

Set these values in the repo-root `.env`:

```bash
PREFECT_API_URL=http://127.0.0.1:4201/api
PROJECT_ROOT=/absolute/path/to/prefect_marimo_starter
PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://prefect:change-me@host.docker.internal:5432/prefect
PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH=prefect_marimo_starter,public
PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_APPLICATION_NAME=prefect-marimo-starter
```

`PROJECT_ROOT` must be the absolute path to this repo on the host machine.
Docker Compose uses it as the bind-mount source path only.

`PREFECT_API_DATABASE_CONNECTION_URL` is the actual Prefect metadata database
connection used by the server container. It must point at a PostgreSQL database
reachable from Docker.

`PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH` isolates this
Prefect server from other Prefect servers sharing the same PostgreSQL database.
Give each repo or server its own unique schema and keep `public` in the search
path so `pg_trgm` and other extensions remain available.

Example when multiple Prefect servers share the same PostgreSQL database:

```bash
PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://prefect:change-me@host.docker.internal:5432/prefect
PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH=prefect_marimo_starter,public
```

Use a different schema for every other Prefect server, for example:

```bash
PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH=other_repo_prefect,public
```

## Multi-Repo Shared PostgreSQL Patterns

If several repos or teams want to use the same PostgreSQL server for independent
Prefect servers, use one of these patterns.

### Option 1: Same Database, Different Schemas

This is the recommended default.

Repo A:

```bash
PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://orbot@host.docker.internal:5432/prefect
PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH=repo_a_prefect,public
```

Repo B:

```bash
PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://orbot@host.docker.internal:5432/prefect
PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH=repo_b_prefect,public
```

This allows the same PostgreSQL database to back multiple independent Prefect
servers while keeping their tables, indexes, blocks, deployments, and flow-run
metadata isolated from one another.

### Option 2: Same PostgreSQL Server, Different Database Name

Use this if you want stronger operational isolation.

Repo A:

```bash
PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://orbot@host.docker.internal:5432/prefect_repo_a
PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH=public
```

Repo B:

```bash
PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://orbot@host.docker.internal:5432/prefect_repo_b
PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH=public
```

This uses a different database name per Prefect server. It is simpler to reason
about for backups and restores, but it creates more databases to manage.

### Collision Rules

- Independent Prefect servers must not share the same schema.
- If they share the same PostgreSQL database, give each one a unique schema.
- If they share the same PostgreSQL server but use a different database name,
  schema collisions are naturally avoided.
- Keep `public` in the search path whenever you use schema isolation, because
  Prefect relies on PostgreSQL extensions such as `pg_trgm`.
- A single logical Prefect server scaled into multiple API containers is a
  different case: those replicas should share one schema and follow Prefect's
  multi-server migration guidance.

## Path Model

The runtime path contract is now repo-native:

- `prefect.yaml` entrypoints stay repo-relative, for example
  `notebooks/financial_monitor/financial_monitor_daily_pipeline.py:run_financial_monitor_daily_pipeline`
- Docker-worker deployments use `set_working_directory` with the fixed internal
  worker path `/opt/prefect/prefect_marimo_starter`
- host `local-process-pool` deployments do not use that Docker-only pull step
- deployments that should honor `.env` config-path settings do not pin config_path
  in `prefect.yaml`
- explicit manual overrides can still use repo-relative paths, for example
  `./config/financial_monitor/financial_monitor_targets.example.yaml`
- shared settings and config loaders resolve relative paths from the repo root,
  not from the current shell working directory
- the Docker worker mounts the repo into `/opt/prefect/prefect_marimo_starter`
  and starts there, so host and container paths no longer need to match

That means `PROJECT_ROOT` is still required for the bind mount source on the
host, but flow code no longer depends on the same absolute path being valid
inside Docker.

## PostgreSQL Bootstrap

The `prefect-server` container runs a small bootstrap step before starting the
API:

- parses `PREFECT_API_DATABASE_CONNECTION_URL`
- creates `pg_trgm` in `public` if needed
- creates the repo-specific schema from the first entry in
  `PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH`

That keeps the simple Compose stack usable even when several Prefect servers
share the same PostgreSQL database.

## Start And Stop

Start the stack:

```bash
docker compose up -d
```

Inspect it:

```bash
docker compose ps
docker compose logs -f prefect-server prefect-worker
curl -sf http://127.0.0.1:4201/api/health
```

Stop it:

```bash
docker compose down
```

If dependencies or the image definition changed, rebuild and recreate:

```bash
docker compose up -d --build --force-recreate
```

## Deploy And Run

Register a deployment from `prefect.yaml`:

```bash
uv run prefect deploy --prefect-file prefect.yaml -n financial-monitor-daily-prod
```

Trigger a dry-run financial-monitor flow through the live server and worker:

```bash
uv run prefect deployment run \
  'financial-monitor-daily-pipeline/financial-monitor-daily-prod' \
  --param config_path='"./config/financial_monitor/financial_monitor_targets.example.yaml"' \
  --param environment='"dev"' \
  --param dry_run=true \
  --watch
```

That path has been validated locally against this Compose stack.

The deployed defaults come from settings in `.env`, not from tracked example
configs. Scheduled or non-dry-run runs should use the real config path. If you
need a manual smoke run with example targets, pass an explicit `config_path`
override at trigger time.

## Container Networking

Flows running inside `prefect-worker` do not reach host services through
`localhost`. If a deployment needs a database or service running directly on
your Mac, use `host.docker.internal` instead.

That applies to settings such as:

- `FINANCIAL_MONITOR_DATABASE_URL`
- `DATABASE_URL`
- `X_MONITOR_DATABASE_URL`

## Recovery And Troubleshooting

If the server fails to start or shows PostgreSQL connection or migration issues:

- stop the stack
- check `docker compose logs prefect-server`
- verify `PREFECT_API_DATABASE_CONNECTION_URL` works from Docker
- verify the configured schema name is unique and includes `public` in the
  search path

If you want to test the local PostgreSQL connection from the host first:

```bash
psql postgres -c '\l'
```

If a flow run is submitted but crashes before task logs appear:

- check `docker compose logs prefect-worker`
- confirm the repo bind mount exists in the worker container
- confirm the relevant config path exists in the mounted repo or override it explicitly

If the worker is running but no pool exists:

- inspect logs with `docker compose logs prefect-worker`
- the worker startup command should create `windows-process-pool` automatically

If flows cannot reach local services:

- replace `localhost` with `host.docker.internal`
- recreate the worker if you changed `.env`

```bash
docker compose up -d --force-recreate
```

If you scale a single Prefect server deployment to multiple API containers
against the same schema, follow Prefect's multi-server guidance:

- use PostgreSQL, not SQLite
- disable automatic migrations on start
- run migrations separately before bringing up multiple API instances

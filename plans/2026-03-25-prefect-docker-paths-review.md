# Prefect Docker Paths Review Context

This file is the handoff context for reviewing the implemented Docker-path
normalization work in `prefect_marimo_starter`.

It is intentionally more specific than the original implementation prompt. The
goal is to help a reviewing agent separate:

- the original path-migration problem statement from the shipped solution
- temporary implementation experiments from the final repo contract
- expected local-operator setup from actual defects

## Review Scope

The implemented slice standardizes how Prefect notebook deployments resolve
repo-local paths when flow runs execute through the local Dockerized Prefect
server and worker.

The shipped behavior includes:

- a fixed in-container repo mount contract at
  `/opt/prefect/prefect_marimo_starter`
- Docker-only `set_working_directory` pull steps for Docker-worker deployments
- repo-root path resolution for shared settings and config loaders
- explicit early errors for missing repo-local config files
- settings-backed deployment defaults for IR and financial monitor scheduled
  runs
- Marimo edit-mode config-path defaults that now honor `.env` overrides

This review context is about path handling and deployment/runtime resolution. It
is not a general review of every notebook's business logic.

## High-Signal Files To Inspect

Read these first:

1. `AGENTS.md`
2. `plans/2026-03-25-prefect-docker-paths-implementation-prompt.md`
3. `plans/2026-03-25-prefect-docker-paths-review.md`
4. `prefect.yaml`
5. `docker-compose.yaml`
6. `src/shared_utils/paths.py`
7. `src/shared_utils/config.py`
8. `src/services/financial_monitor/financial_monitor_config.py`
9. `src/services/ir_monitor/ir_monitor_config_loader.py`
10. `src/services/x_monitor/x_monitor_config_loader.py`
11. `src/services/ir_monitor/ir_monitor_jobs_builder.py`
12. `notebooks/ir/ir_webchanges_monitor.py`
13. `notebooks/financial_monitor/financial_monitor_daily_pipeline.py`
14. `docs/prefect/prefect_local_dev_stack.md`
15. `docs/financial_monitor/financial_monitor_setup.md`

Read these as supporting context:

1. `docs/ADDING_FLOWS.md`
2. `README.md`
3. `tests/unit/test_config.py`
4. `tests/unit/test_prefect_postgres.py`
5. `tests/unit/financial_monitor/test_financial_monitor_config.py`
6. `tests/unit/financial_monitor/test_financial_monitor_deployment_docs.py`
7. `tests/unit/financial_monitor/test_financial_monitor_notebook_flow.py`
8. `tests/unit/ir_monitor/test_ir_monitor_config_loader.py`
9. `tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py`
10. `tests/unit/ir_monitor/test_ir_monitor_jobs_builder.py`
11. `tests/unit/ir_monitor/test_ir_monitor_notebook_flow.py`
12. `tests/unit/x_monitor/test_x_monitor_config_loader.py`
13. `tests/unit/x_monitor/test_x_monitor_deployment_docs.py`

## What Changed Relative To The Original Prompt

The final implementation differs from the original prompt in a few important
ways.

### 1. `set_working_directory` was not removed entirely

The original problem statement called out a host-specific absolute pull step.
The final fix does not eliminate `set_working_directory`; it narrows and
normalizes it.

Shipped behavior:

- Docker-worker deployments use an anchored pull step that sets the working
  directory to `/opt/prefect/prefect_marimo_starter`
- the pull step is attached only to deployments that run through the Docker
  worker and `windows-process-pool`
- X-monitor deployments use `local-process-pool` and do not include that Docker
  pull step

Reviewer focus:

- confirm the Docker pull step is scoped only to Docker-worker deployments
- confirm no host-specific absolute path remains in deployment pull config

### 2. Scheduled deployment defaults now come from settings-backed notebook parameters

An intermediate implementation used tracked example configs as deployment
defaults for IR and financial monitor. That was later tightened.

Shipped behavior:

- `prefect.yaml` no longer passes `config_path` for the production IR and
  financial-monitor deployments
- the effective defaults now come from notebook function signatures, which read
  `SETTINGS.ir_monitor_config_path` and
  `SETTINGS.financial_monitor_config_path`
- the repo still tracks example configs for manual smoke runs and onboarding,
  but scheduled runs are expected to use the real config path from `.env`

Reviewer focus:

- confirm the deployment defaults and docs now match each other
- confirm scheduled runs do not silently fall back to example configs

### 3. Shared path resolution is now repo-root aware

The implementation introduced a shared repo-path helper layer so path handling
is not hard-coded per notebook.

Shipped behavior:

- `src/shared_utils/paths.py` resolves repo-relative paths from the repo root
- `src/shared_utils/config.py` resolves configured repo-path fields from the
  repo root instead of the current shell working directory
- config loaders for IR, financial monitor, and X monitor use the shared helper
  and raise repo-aware missing-file errors
- the IR jobs builder resolves its normalizer script from the repo root instead
  of the process working directory

Reviewer focus:

- confirm the shared helper is used consistently in the affected workflows
- confirm missing-file messages are explicit enough for operators

### 4. Marimo edit mode now aligns with `.env` config overrides

One low-severity follow-up review finding remained after the main path work:
the IR and financial-monitor flow defaults honored `.env`, but the edit-mode
text inputs still seeded from repo/example constants.

That finding is now fixed.

Shipped behavior:

- IR edit mode uses a helper that prefers the customized settings path when
  `IR_MONITOR_CONFIG_PATH` differs from the repo default
- financial-monitor edit mode does the same for
  `FINANCIAL_MONITOR_CONFIG_PATH`
- when the settings path is still the repo default, edit mode keeps the
  original repo/example fallback behavior

Reviewer focus:

- confirm the edit-mode widget default now matches the actual flow default when
  `.env` overrides are present
- confirm the repo/example fallback still works for the uncustomized case

## Local Environment Notes For Review

These are expected environment conditions, not feature bugs by themselves:

- a gitignored repo-root `.env` may define real config paths for IR and
  financial monitor
- `PROJECT_ROOT` in `.env` is the host bind-mount source path, not the
  in-container execution path
- flows running inside the Docker worker do not reach host services through
  `localhost`; operator config must use `host.docker.internal` for host-local
  services
- local flow runs may generate repo-local artifacts under `data/` or `reports/`
  unless cleaned up after verification

## Verified State At Time Of This Handoff

The following verification was run successfully during the implementation and
follow-up review-fix session:

```bash
uv run pytest tests/unit/financial_monitor tests/unit/ir_monitor tests/unit/x_monitor tests/unit/test_config.py tests/unit/test_prefect_postgres.py -v
uv run pytest tests/unit/ir_monitor/test_ir_monitor_notebook_flow.py tests/unit/financial_monitor/test_financial_monitor_notebook_flow.py -v
uvx ruff check src/shared_utils notebooks tests/unit
uvx ruff check notebooks/ir/ir_webchanges_monitor.py notebooks/financial_monitor/financial_monitor_daily_pipeline.py tests/unit/ir_monitor/test_ir_monitor_notebook_flow.py tests/unit/financial_monitor/test_financial_monitor_notebook_flow.py
uv run marimo check notebooks/financial_monitor/financial_monitor_daily_pipeline.py notebooks/ir/ir_webchanges_monitor.py notebooks/x_monitor/x_monitor_poll_accounts.py notebooks/x_monitor/x_monitor_send_digest.py notebooks/x_monitor/x_monitor_healthcheck.py
docker compose config
docker compose up -d --build --force-recreate
uv run prefect deploy --prefect-file prefect.yaml -n financial-monitor-daily-prod
uv run prefect deploy --prefect-file prefect.yaml -n ir-webchanges-monitor-prod
uv run prefect deployment run 'financial-monitor-daily-pipeline/financial-monitor-daily-prod' --param dry_run=true --watch
uv run prefect deployment run 'ir-webchanges-monitor/ir-webchanges-monitor-prod' --param dry_run=true --watch
```

Observed implementation-session outcomes:

- unit suites covering financial monitor, IR monitor, X monitor, shared config,
  and Prefect PostgreSQL bootstrap passed
- targeted notebook-flow regression tests for the edit-mode config default fix
  passed
- Ruff checks passed
- Marimo notebook checks passed
- Docker Compose rendered and rebuilt successfully
- financial-monitor and IR production deployments registered successfully
- representative financial-monitor and IR dry runs completed through the live
  Dockerized local Prefect server and worker

## Residual Limitation

One operator-facing limitation remains intentionally unresolved:

- service URLs that point at host-local resources still cannot use `localhost`
  from code running inside the Docker worker; operators must configure those
  URLs with `host.docker.internal` or another Docker-reachable hostname

That is now documented and treated as environment setup, not as an implicit
runtime rewrite performed by the code.

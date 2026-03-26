# Follow-Up Prompt: Fix Dockerized Prefect Path Assumptions Repo-Wide

You are working in the `prefect_marimo_starter` repository.

Start from commit `045668a`:

```bash
git checkout 045668a
```

## Objective

Fix the remaining path-resolution problems that appear when Prefect flows run
through the Dockerized local Prefect server and worker.

The current repo now has:

- a repo-local Docker Compose Prefect stack
- a Dockerized Prefect server backed by PostgreSQL
- a Dockerized Prefect worker that bind-mounts the repo at `PROJECT_ROOT`
- a working financial-monitor deployment registration path

However, there are still repo-wide path assumptions that break once flow runs
execute inside Docker instead of directly on the host.

## Problem Statement

The current Docker worker can execute flows, but many path assumptions are still
host-oriented:

1. `prefect.yaml` still uses a host-specific absolute `set_working_directory`
   pull step.
2. Some deployments reference local config files such as:

   - `config/financial_monitor/financial_monitor_targets.yaml`
   - similar untracked `config/.../*.yaml` files in other workflows

3. Relative local file paths may work on the host but fail inside the worker if
   the files are untracked, missing, or expected to exist outside the repo.
4. Service URLs that use `localhost` from flow code will not reach host-local
   services when the code is running inside the worker container.
5. This likely affects more than just the financial monitor.

## Your Task

Audit the repo and implement a repo-native solution for path handling in Docker
Prefect runs.

Do not just patch the financial monitor in isolation unless your audit proves
the problem is unique to that flow.

## Constraints

Follow this repo’s existing conventions:

- unified Marimo + Prefect notebooks
- `@app.function` stacked above `@task` / `@flow`
- no `sys.path.append(...)`
- import repo packages directly
- use unit tests only
- mock external dependencies
- keep notebooks orchestration-focused

Do not:

- remove the notebook-first architecture
- create a second standalone flow runner
- bypass Prefect deployments
- switch to a different runtime model

## Files To Study First

- `AGENTS.md`
- `prefect.yaml`
- `docker-compose.yaml`
- `docs/prefect/prefect_local_dev_stack.md`
- `docs/ADDING_FLOWS.md`
- `docs/financial_monitor/financial_monitor_setup.md`
- `notebooks/financial_monitor/financial_monitor_daily_pipeline.py`
- `notebooks/ir/ir_webchanges_monitor.py`
- `notebooks/x_monitor/`
- `src/shared_utils/config.py`
- `src/shared_utils/prefect_postgres.py`
- tests under `tests/unit/financial_monitor/`

## Desired End State

1. Dockerized Prefect deployments do not rely on host-specific absolute paths.
2. Repo-local config resolution is explicit and testable.
3. Flows that need local config files either:
   - resolve a repo-mounted path correctly inside Docker, or
   - fail with a clear configuration error and documented setup path.
4. The local Docker worker can execute representative flows without path
   failures caused by:
   - missing `set_working_directory`
   - missing config files
   - host-only absolute paths
5. The solution is reusable across workflows, not hand-coded per notebook unless
   justified.

## Suggested Approach

1. Audit every deployment in `prefect.yaml` for file-path assumptions.
2. Identify all notebooks/services that consume local paths from parameters or
   settings.
3. Introduce a shared path-resolution strategy if the audit shows repeated
   patterns.
4. Replace host-specific absolute path assumptions with repo-aware or
   environment-aware resolution.
5. Improve error messages where untracked local config files are genuinely
   required.
6. Update docs so Docker-prefect execution rules are explicit.

## Specific Things To Evaluate

### A. `prefect.yaml` Pull Step

Determine whether the current absolute pull step should be replaced by:

- an environment-aware project-root setting
- a relative repo-root strategy
- a Docker/host compatible path contract

The outcome must work for both:

- host-side `prefect deploy`
- Docker worker execution

### B. Config Files

Evaluate every deployment parameter that points at a local config file.

For each one, decide whether it should:

- point at a tracked example by default
- require an explicit local override
- resolve via env var or settings
- validate existence early with a helpful error

### C. Host Service Access

Audit whether notebooks or shared services use `localhost` for resources that
will be consumed from inside Docker.

Where appropriate, document or normalize the Docker-compatible host value.

## Testing Protocol

Use TDD for behavior changes:

1. write the failing test first
2. run the targeted test and confirm the expected failure
3. implement the minimum fix
4. rerun the targeted test
5. continue

## Minimum Verification

At minimum, run the relevant targeted tests plus:

```bash
uv run pytest tests/unit/financial_monitor tests/unit/test_config.py tests/unit/test_prefect_postgres.py -v
uvx ruff check src/shared_utils notebooks tests/unit
uv run marimo check notebooks/financial_monitor/financial_monitor_daily_pipeline.py
docker compose config
docker compose up -d --build --force-recreate
uv run prefect deploy --prefect-file prefect.yaml -n financial-monitor-daily-prod
```

If you change other notebook families, add their notebook checks too.

## Deliverables

1. the code changes
2. updated docs
3. a concise explanation of the path model
4. verification results
5. any residual limitations that still require operator setup

## Important Context

The current Dockerized financial-monitor deployment was successfully registered
and run with explicit example-config overrides, but the repo still needs a
general fix for default path assumptions. Solve that general problem, not just
the one successful demo path.

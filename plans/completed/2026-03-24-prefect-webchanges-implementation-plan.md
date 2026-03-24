# Japanese IR Webchanges Monitor Implementation Plan

> **Status:** COMPLETE
> **Completed:** 2026-03-24
> **Archive:** condensed from the original implementation plan, implementation prompt, master program, and ticker-grouping follow-up prompt.

**Goal:** Ship a repo-native IR monitor that runs as a unified Marimo + Prefect notebook, uses `webchanges` for stateful diffing, and publishes grouped artifacts and notifications for configured IR/news targets.

## Delivered

- Added `src/services/ir_monitor/` for config loading, normalization, job generation, webchanges execution, report parsing, artifact writing, notification formatting, and shared display helpers.
- Added `notebooks/ir/ir_webchanges_monitor.py` as the orchestration entrypoint, plus deployment, example config, and user-facing docs.
- Added optional `companies` registry support so `company_name`, `ticker`, and `exchange` resolve once per `company_id`.
- Added a follow-up config cleanup that separates run-level settings into top-level `runtime` and narrows selector validation to the supported surface.

## Final Contract

- `companies` is optional and keyed by `company_id`; it supplies canonical `name`, `ticker`, and `exchange`.
- `runtime` is optional and carries `workspace_dir`, `notify_on_no_change`, and `schedule_cron`.
- Legacy runtime-like keys under `defaults` are still accepted and normalized into `config.runtime`.
- Workspace resolution order is: flow parameter -> `config.runtime.workspace_dir` -> `SETTINGS.ir_monitor_workspace_dir / environment`.
- Notification override order is: flow parameter -> `config.runtime.notify_on_no_change`.
- Grouping and display use `Company Name (TICKER)` when a ticker exists and `Company Name` otherwise.

## Important Deviations

- `webchanges==3.34.2` did not provide the changed-jobs payload assumed by the early plan. The final runtime treats stdout as the diff source of truth; structured sidecar data is optional.
- The generated jobs file uses multi-document YAML and `additions_only: true`, matching the format `webchanges` actually accepts.
- The runtime/config split was delivered after the main feature landed, then folded into the final documented contract.

## Verification At Completion

- `uv run pytest tests/unit/ir_monitor -v`
- `uv run pytest tests/unit/test_config.py tests/unit/test_prefect_notifications.py -v`
- `uv run ruff check src/services/ir_monitor scripts/ir_monitor notebooks/ir/ir_webchanges_monitor.py tests/unit/ir_monitor`
- `uv run marimo check notebooks/ir/ir_webchanges_monitor.py`

## Canonical References

- `docs/specs/prefect_webchanges.md`
- `docs/ir_monitor/IR_MONITOR_OVERVIEW.md`
- `docs/ir_monitor/IR_MONITOR_CONFIGURATION.md`

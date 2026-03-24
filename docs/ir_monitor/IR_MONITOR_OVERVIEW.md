# IR Monitor Overview

The IR monitor workflow lives at `notebooks/ir/ir_webchanges_monitor.py`.

It monitors configured IR/news targets with `webchanges`, parses change output into
structured events, writes timestamped artifacts, and sends content notifications when
real changes are detected.

## Main Components

- Notebook flow: `notebooks/ir/ir_webchanges_monitor.py`
- Config loader: `src/services/ir_monitor/ir_monitor_config_loader.py`
- Models: `src/services/ir_monitor/ir_monitor_models.py`
- Normalizers: `src/services/ir_monitor/normalizers/`
- Report parser: `src/services/ir_monitor/ir_monitor_report_parser.py`
- Artifacts: `src/services/ir_monitor/ir_monitor_artifacts.py`
- Notifications: `src/services/ir_monitor/ir_monitor_notifier.py`

## Runtime Behavior

1. Load the YAML config from `config/ir_monitor/`.
2. Resolve company metadata, defaults, and enabled targets.
3. Build a durable `webchanges` workspace under the configured environment path.
4. Initialize baselines for newly added targets with `--prepare-jobs`.
5. Run `webchanges` against all enabled targets.
6. Parse stdout into structured change events and enrich them with target metadata.
7. Write run artifacts:
   - `raw_report.txt`
   - `changes.json`
   - `changes.md`
8. Register the Markdown summary as a Prefect artifact.
9. Send a webhook notification for content changes, or fall back to log-only output.

## Company Registry

The config supports an optional top-level `companies` mapping keyed by `company_id`.

This lets multiple targets share one canonical company identity:

- `name`
- `ticker`
- `exchange`

If a target `company_id` matches a `companies` entry, the company registry overrides the
target-level `company_name` and also supplies `ticker` and `exchange`.

If `companies` is absent, the target-level `company_name` path continues to work.

## Display Rules

- Artifacts group events by `Company Name (TICKER)` when a ticker exists.
- Notifications use the same label.
- If `ticker` is empty, the display falls back to `Company Name`.

## Local Commands

Run the notebook as a script:

```bash
uv run python notebooks/ir/ir_webchanges_monitor.py
```

Run the focused verification suite:

```bash
uv run pytest tests/unit/ir_monitor -v
uv run pytest tests/unit/test_config.py tests/unit/test_prefect_notifications.py -v
uv run ruff check src/services/ir_monitor scripts/ir_monitor notebooks/ir/ir_webchanges_monitor.py tests/unit/ir_monitor
uv run marimo check notebooks/ir/ir_webchanges_monitor.py
```

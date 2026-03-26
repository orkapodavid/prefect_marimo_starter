# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "prefect>=3.0.0,<4.0.0",
#     "jinja2>=3.1.0",
#     "pydantic>=2.0.0",
#     "pydantic-settings>=2.0.0",
#     "pyyaml>=6.0",
#     "sqlalchemy>=2.0.0",
#     "twscrape>=0.12.0",
#     "google-api-python-client>=2.100.0",
#     "google-auth>=2.23.0",
#     "google-auth-oauthlib>=1.1.0",
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup:
    from datetime import UTC, datetime
    import json
    from pathlib import Path
    from uuid import uuid4

    from prefect import flow, task
    from sqlalchemy import insert

    from services.x_monitor.x_monitor_bootstrap import bootstrap_target
    from services.x_monitor.x_monitor_cli import (
        _build_email_provider as build_email_provider,
    )
    from services.x_monitor.x_monitor_cli import (
        _build_twscrape_client as build_twscrape_client,
    )
    from services.x_monitor.x_monitor_config_loader import load_x_monitor_config
    from services.x_monitor.x_monitor_database import get_x_monitor_engine
    from services.x_monitor.x_monitor_polling import (
        build_poll_run_summary,
        poll_single_target,
    )
    from services.x_monitor.x_monitor_tables import X_MONITOR_METADATA
    from services.x_monitor.x_monitor_targets_sync import list_targets, sync_targets
    from shared_utils.config import get_settings
    from shared_utils.prefect_notifications import notify_on_failure

    SETTINGS = get_settings()
    REPO_X_MONITOR_CONFIG_PATH = str(SETTINGS.x_monitor_config_path)
    tbl_x_monitor_flow_runs = X_MONITOR_METADATA.tables["tblXMonitorFlowRuns"]


# ============================================================
# TASKS
# ============================================================


@app.function
@task(retries=2, retry_delay_seconds=30)
def load_config(config_path: str):
    """Load the X monitor YAML configuration."""
    return load_x_monitor_config(Path(config_path))


@app.function
@task(retries=2, retry_delay_seconds=30)
def sync_config_targets(config, environment: str = "dev") -> list[dict]:
    """Reconcile YAML targets into the database."""
    engine = get_x_monitor_engine()
    sync_targets(engine, [target.model_dump() for target in config.targets])
    return list_targets(engine, include_inactive=True)


@app.function
@task(retries=2, retry_delay_seconds=30)
def resolve_user_ids(config) -> list[dict]:
    """Bootstrap targets with missing user ids and first-run watermarks."""
    engine = get_x_monitor_engine()
    client = build_twscrape_client(SETTINGS)
    resolved_targets = []
    for target in config.targets:
        target_payload = target.model_dump()
        if target_payload.get("active") and not target_payload.get("user_id"):
            resolved_targets.append(bootstrap_target(engine, client, target_payload))
    return resolved_targets


@app.function
@task(retries=2, retry_delay_seconds=30)
def poll_targets(config) -> list[dict]:
    """Poll every active target for unseen posts."""
    engine = get_x_monitor_engine()
    client = build_twscrape_client(SETTINGS)
    email_provider = build_email_provider(SETTINGS)
    return [
        poll_single_target(
            engine=engine,
            client=client,
            email_provider=email_provider,
            target=target.model_dump(),
            settings=SETTINGS,
        )
        for target in config.targets
        if target.active
    ]


@app.function
@task(retries=2, retry_delay_seconds=30)
def record_run_summary(results: list[dict]) -> dict:
    """Persist the flow-level summary and return it."""
    summary = build_poll_run_summary(results)
    engine = get_x_monitor_engine()
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            insert(tbl_x_monitor_flow_runs).values(
                id=str(uuid4()),
                flow_name="x-monitor-poll-accounts",
                prefect_flow_run_id=None,
                started_at=now,
                finished_at=now,
                status="completed",
                counts_json=summary,
                error_message=None,
            )
        )
    return summary


# ============================================================
# FLOW
# ============================================================


@app.function
@flow(name="x-monitor-poll-accounts", log_prints=True, on_failure=[notify_on_failure])
def run_x_monitor_poll_accounts(
    config_path: str = REPO_X_MONITOR_CONFIG_PATH,
    environment: str = "dev",
) -> dict:
    """Poll configured X accounts for new posts and send immediate alerts."""
    config = load_config(config_path=config_path)
    synced_targets = sync_config_targets(config=config, environment=environment)
    bootstrapped_targets = resolve_user_ids(config=config)
    poll_results = poll_targets(config=config)
    summary = record_run_summary(results=poll_results)
    return {
        "environment": environment,
        "config_path": config_path,
        "synced_targets": synced_targets,
        "bootstrapped_targets": bootstrapped_targets,
        "summary": summary,
        "poll_results": poll_results,
    }


# ============================================================
# INTERACTIVE CELLS (edit mode only)
# ============================================================


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    config_path_input = None
    environment_select = None
    run_button = None
    ui = None

    if mo.app_meta().mode == "edit":
        config_path_input = mo.ui.text(
            value=REPO_X_MONITOR_CONFIG_PATH,
            label="Config Path",
            full_width=True,
        )
        environment_select = mo.ui.dropdown(
            options=["dev", "prod"],
            value="dev",
            label="Environment",
        )
        run_button = mo.ui.run_button(label="Run X Monitor Poll")
        ui = mo.vstack([config_path_input, environment_select, run_button])

    ui
    return config_path_input, environment_select, run_button


@app.cell
def _(config_path_input, environment_select, mo, run_button):
    interactive_result = None

    if mo.app_meta().mode == "edit" and run_button and run_button.value:
        interactive_result = run_x_monitor_poll_accounts(
            config_path=config_path_input.value,
            environment=environment_select.value,
        )

    return (interactive_result,)


@app.cell
def _(interactive_result, mo):
    preview_view = None

    if mo.app_meta().mode == "edit":
        preview_view = mo.md(
            "No poll run has been triggered yet."
            if interactive_result is None
            else f"```json\n{json.dumps(interactive_result, ensure_ascii=False, indent=2)}\n```"
        )

    preview_view
    return


# ============================================================
# SCRIPT EXECUTION (production)
# ============================================================


@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        result = run_x_monitor_poll_accounts()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return


if __name__ == "__main__":
    app.run()

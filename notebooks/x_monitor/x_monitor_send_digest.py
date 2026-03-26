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

    from services.x_monitor.x_monitor_cli import (
        _build_email_provider as build_email_provider,
    )
    from services.x_monitor.x_monitor_config_loader import load_x_monitor_config
    from services.x_monitor.x_monitor_database import get_x_monitor_engine
    from services.x_monitor.x_monitor_digest import (
        collect_digest_items,
        compute_digest_window,
        group_digest_items,
        send_digest_for_recipient,
    )
    from services.x_monitor.x_monitor_tables import X_MONITOR_METADATA
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
    """Load the X monitor digest configuration."""
    return load_x_monitor_config(Path(config_path))


@app.function
@task(retries=2, retry_delay_seconds=30)
def compute_window(timezone: str):
    """Compute the digest window for the selected timezone."""
    return compute_digest_window(timezone)


@app.function
@task(retries=2, retry_delay_seconds=30)
def collect_items(window):
    """Collect undigested items for the current digest window."""
    engine = get_x_monitor_engine()
    return collect_digest_items(engine, window_start=window[0], window_end=window[1])


@app.function
@task(retries=2, retry_delay_seconds=30)
def send_digests(items: list[dict], window) -> list[dict]:
    """Send one digest per recipient."""
    engine = get_x_monitor_engine()
    email_provider = build_email_provider(SETTINGS)
    grouped_items = group_digest_items(items)
    results = []
    for recipient, account_items in grouped_items.items():
        flattened_items = [
            {**item, "recipient": recipient}
            for posts in account_items.values()
            for item in posts
        ]
        results.append(
            send_digest_for_recipient(
                engine=engine,
                email_provider=email_provider,
                recipient=recipient,
                items=flattened_items,
                window=window,
                settings=SETTINGS,
            )
        )
    return results


@app.function
@task(retries=2, retry_delay_seconds=30)
def record_run_summary(results: list[dict]) -> dict:
    """Persist the digest flow summary."""
    summary = {
        "digests_attempted": len(results),
        "digests_sent": sum(1 for result in results if result.get("sent")),
        "digests_failed": sum(1 for result in results if result.get("status") == "failed"),
    }
    engine = get_x_monitor_engine()
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            insert(tbl_x_monitor_flow_runs).values(
                id=str(uuid4()),
                flow_name="x-monitor-send-digest",
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
@flow(name="x-monitor-send-digest", log_prints=True, on_failure=[notify_on_failure])
def run_x_monitor_send_digest(
    config_path: str = REPO_X_MONITOR_CONFIG_PATH,
    environment: str = "dev",
) -> dict:
    """Send daily digest emails for matched X monitor posts."""
    config = load_config(config_path=config_path)
    window = compute_window(config.runtime.timezone)
    items = collect_items(window=window)
    digest_results = send_digests(items=items, window=window)
    summary = record_run_summary(results=digest_results)
    return {
        "environment": environment,
        "config_path": config_path,
        "window": [window[0].isoformat(), window[1].isoformat()],
        "items": items,
        "digest_results": digest_results,
        "summary": summary,
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
        run_button = mo.ui.run_button(label="Send X Monitor Digest")
        ui = mo.vstack([config_path_input, environment_select, run_button])

    ui
    return config_path_input, environment_select, run_button


@app.cell
def _(config_path_input, environment_select, mo, run_button):
    interactive_result = None

    if mo.app_meta().mode == "edit" and run_button and run_button.value:
        interactive_result = run_x_monitor_send_digest(
            config_path=config_path_input.value,
            environment=environment_select.value,
        )

    return (interactive_result,)


@app.cell
def _(interactive_result, mo):
    preview_view = None

    if mo.app_meta().mode == "edit":
        preview_view = mo.md(
            "No digest run has been triggered yet."
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
        result = run_x_monitor_send_digest()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return


if __name__ == "__main__":
    app.run()

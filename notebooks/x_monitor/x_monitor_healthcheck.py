# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "prefect>=3.0.0,<4.0.0",
#     "pydantic>=2.0.0",
#     "pydantic-settings>=2.0.0",
#     "pyyaml>=6.0",
#     "sqlalchemy>=2.0.0",
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup:
    from datetime import UTC, datetime
    import json
    from pathlib import Path
    from urllib.error import URLError
    from urllib.request import urlopen
    from uuid import uuid4

    from prefect import flow, task
    from sqlalchemy import insert, text

    from services.x_monitor.x_monitor_config_loader import load_x_monitor_config
    from services.x_monitor.x_monitor_database import get_x_monitor_engine
    from services.x_monitor.x_monitor_tables import X_MONITOR_METADATA
    from shared_utils.config import get_settings
    from shared_utils.prefect_notifications import notify_on_failure

    SETTINGS = get_settings()
    tbl_x_monitor_flow_runs = X_MONITOR_METADATA.tables["tblXMonitorFlowRuns"]
    tbl_x_monitor_operator_events = X_MONITOR_METADATA.tables["tblXMonitorOperatorEvents"]


# ============================================================
# TASKS
# ============================================================


@app.function
@task(retries=2, retry_delay_seconds=30)
def load_config(config_path: str):
    """Load the X monitor configuration for health checks."""
    return load_x_monitor_config(Path(config_path))


@app.function
@task(retries=2, retry_delay_seconds=30)
def check_database() -> dict:
    """Verify the X monitor database is reachable."""
    try:
        with get_x_monitor_engine().connect() as connection:
            connection.execute(text("select 1"))
        return {"check": "database", "ok": True}
    except Exception as exc:  # pragma: no cover - exercised by manual smoke tests
        return {"check": "database", "ok": False, "error": str(exc)}


@app.function
@task(retries=2, retry_delay_seconds=30)
def check_prefect(api_url: str | None) -> dict:
    """Verify the Prefect API is reachable."""
    if not api_url:
        return {"check": "prefect", "ok": False, "error": "PREFECT_API_URL is not configured"}

    try:
        with urlopen(api_url, timeout=5) as response:
            return {"check": "prefect", "ok": 200 <= response.status < 500}
    except URLError as exc:  # pragma: no cover - exercised by manual smoke tests
        return {"check": "prefect", "ok": False, "error": str(exc)}


@app.function
@task(retries=2, retry_delay_seconds=30)
def check_twscrape(accounts_db: str) -> dict:
    """Verify the twscrape accounts database exists."""
    accounts_path = Path(accounts_db)
    if accounts_path.exists():
        return {"check": "twscrape", "ok": True, "path": str(accounts_path)}
    return {"check": "twscrape", "ok": False, "error": f"Missing {accounts_path}"}


@app.function
@task(retries=2, retry_delay_seconds=30)
def check_gmail() -> dict:
    """Verify Gmail provider configuration is present."""
    provider = SETTINGS.x_monitor_gmail_provider
    if provider == "gmail_smtp":
        ok = bool(SETTINGS.x_monitor_gmail_smtp_username and SETTINGS.x_monitor_gmail_smtp_from)
        return {"check": "gmail", "ok": ok, "provider": provider}
    if provider == "gmail_api":
        ok = bool(
            SETTINGS.x_monitor_gmail_api_use_adc
            or SETTINGS.x_monitor_gmail_api_credentials_file
        )
        return {"check": "gmail", "ok": ok, "provider": provider}
    return {"check": "gmail", "ok": False, "provider": provider}


@app.function
@task(retries=2, retry_delay_seconds=30)
def record_health_results(results: list[dict]) -> dict:
    """Persist healthcheck status and operator events when needed."""
    engine = get_x_monitor_engine()
    now = datetime.now(UTC)
    summary = {
        "checks": results,
        "healthy": all(result.get("ok") for result in results),
    }
    with engine.begin() as connection:
        connection.execute(
            insert(tbl_x_monitor_flow_runs).values(
                id=str(uuid4()),
                flow_name="x-monitor-healthcheck",
                prefect_flow_run_id=None,
                started_at=now,
                finished_at=now,
                status="completed" if summary["healthy"] else "failed",
                counts_json=summary,
                error_message=None if summary["healthy"] else "One or more health checks failed",
            )
        )
        for result in results:
            if result.get("ok"):
                continue
            connection.execute(
                insert(tbl_x_monitor_operator_events).values(
                    id=str(uuid4()),
                    event_type="healthcheck_failure",
                    severity="error",
                    message=f"X monitor {result['check']} check failed",
                    details_json=result,
                    created_at=now,
                    dedupe_key=f"healthcheck:{result['check']}",
                )
            )
    return summary


# ============================================================
# FLOW
# ============================================================


@app.function
@flow(name="x-monitor-healthcheck", log_prints=True, on_failure=[notify_on_failure])
def run_x_monitor_healthcheck(
    config_path: str = "./config/x_monitor/x_monitor_targets.yaml",
    environment: str = "dev",
) -> dict:
    """Run infrastructure health checks for the X monitor stack."""
    config = load_config(config_path=config_path)
    results = [
        check_database(),
        check_prefect(SETTINGS.prefect_api_url),
        check_twscrape(str(SETTINGS.x_monitor_twscrape_accounts_db)),
        check_gmail(),
    ]
    summary = record_health_results(results=results)
    return {
        "environment": environment,
        "config_path": config_path,
        "timezone": config.runtime.timezone,
        "results": results,
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
            value="./config/x_monitor/x_monitor_targets.yaml",
            label="Config Path",
            full_width=True,
        )
        environment_select = mo.ui.dropdown(
            options=["dev", "prod"],
            value="dev",
            label="Environment",
        )
        run_button = mo.ui.run_button(label="Run X Monitor Healthcheck")
        ui = mo.vstack([config_path_input, environment_select, run_button])

    ui
    return config_path_input, environment_select, run_button


@app.cell
def _(config_path_input, environment_select, mo, run_button):
    interactive_result = None

    if mo.app_meta().mode == "edit" and run_button and run_button.value:
        interactive_result = run_x_monitor_healthcheck(
            config_path=config_path_input.value,
            environment=environment_select.value,
        )

    return (interactive_result,)


@app.cell
def _(interactive_result, mo):
    preview_view = None

    if mo.app_meta().mode == "edit":
        preview_view = mo.md(
            "No healthcheck run has been triggered yet."
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
        result = run_x_monitor_healthcheck()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return


if __name__ == "__main__":
    app.run()

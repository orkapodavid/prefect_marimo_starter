# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "prefect>=3.0.0,<4.0.0",
#     "pydantic>=2.0.0",
#     "pydantic-settings>=2.0.0",
#     "pyyaml>=6.0",
#     "webchanges==3.34.2",
#     "beautifulsoup4>=4.12.0",
#     "lxml>=5.0.0",
#     "pypdf>=5.0.0",
#     "requests>=2.31.0",
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup:
    from datetime import datetime
    import json
    from pathlib import Path
    from zoneinfo import ZoneInfo

    from prefect import flow, task
    from prefect.artifacts import create_markdown_artifact

    from services.ir_monitor.ir_monitor_artifacts import (
        write_run_artifacts as write_run_artifacts_service,
    )
    from services.ir_monitor.ir_monitor_config_loader import (
        load_monitor_config as load_monitor_config_service,
    )
    from services.ir_monitor.ir_monitor_jobs_builder import build_workspace_files
    from services.ir_monitor.ir_monitor_models import (
        ArtifactPaths,
        CommandResult,
        MonitorConfig,
        NotificationResult,
        ParsedMonitorReport,
        WorkspacePaths,
    )
    from services.ir_monitor.ir_monitor_notifier import (
        notify_if_needed as notify_if_needed_service,
    )
    from services.ir_monitor.ir_monitor_report_parser import (
        parse_monitor_report as parse_monitor_report_service,
    )
    from services.ir_monitor.ir_monitor_runner import run_webchanges_command
    from shared_utils.config import get_settings
    from shared_utils.prefect_notifications import notify_on_failure

    SETTINGS = get_settings()

    def _load_known_baseline_ids(path: Path) -> set[str]:
        if not path.exists():
            return set()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return set()
        return set(payload.get("baseline_target_ids", []))

    def _target_metadata_by_id(config: MonitorConfig) -> dict[str, dict[str, str]]:
        return {
            target.id: {
                "company_id": target.company_id,
                "company_name": target.company_name,
                "ticker": target.ticker,
                "exchange": target.exchange,
                "page_label": target.page_label,
                "diff_mode": target.diff_mode or "additions_only",
            }
            for target in config.targets
            if target.enabled
        }

    def _resolve_workspace_dir(
        config: MonitorConfig,
        environment: str,
        workspace_dir: str | None = None,
    ) -> Path:
        if workspace_dir:
            return Path(workspace_dir)
        if config.runtime.workspace_dir is not None:
            return config.runtime.workspace_dir
        return SETTINGS.ir_monitor_workspace_dir / environment

    def _resolve_notify_on_no_change(
        config: MonitorConfig,
        notify_on_no_change: bool | None = None,
    ) -> bool:
        if notify_on_no_change is not None:
            return notify_on_no_change
        return config.runtime.notify_on_no_change

    def _raise_for_failed_webchanges_run(
        command_result: CommandResult,
        parsed_report: ParsedMonitorReport,
        artifact_paths: ArtifactPaths,
    ) -> None:
        if command_result.exit_code == 0:
            return

        failed_target_suffix = ""
        if parsed_report.failed_target_ids:
            failed_target_suffix = (
                f" Failed targets: {', '.join(sorted(parsed_report.failed_target_ids))}."
            )
        raise RuntimeError(
            "webchanges exited with code "
            f"{command_result.exit_code}.{failed_target_suffix} "
            f"See {artifact_paths.raw_report_path} for details."
        )


# ============================================================
# TASKS
# ============================================================


@app.function
@task(retries=2, retry_delay_seconds=30)
def load_monitor_config(config_path: str) -> MonitorConfig:
    """Load and validate the IR monitor config file."""
    return load_monitor_config_service(Path(config_path))


@app.function
@task(retries=2, retry_delay_seconds=30)
def prepare_workspace(
    config: MonitorConfig,
    environment: str,
    workspace_dir: str | None = None,
) -> WorkspacePaths:
    """Resolve and prepare the durable workspace."""
    resolved_workspace_dir = _resolve_workspace_dir(
        config=config,
        environment=environment,
        workspace_dir=workspace_dir,
    )
    return build_workspace_files(config=config, workspace_dir=resolved_workspace_dir)


@app.function
@task(retries=2, retry_delay_seconds=30)
def run_webchanges(
    workspace: WorkspacePaths,
    new_target_ids: list[str],
    dry_run: bool = False,
) -> CommandResult:
    """Run webchanges, or skip execution in dry-run mode."""
    if dry_run:
        workspace.changed_jobs_path.parent.mkdir(parents=True, exist_ok=True)
        workspace.changed_jobs_path.write_text("", encoding="utf-8")
        return CommandResult(
            exit_code=0,
            stdout="Dry run: webchanges execution skipped.",
            stderr="",
            changed_jobs_path=workspace.changed_jobs_path,
            baseline_target_ids=new_target_ids,
        )

    return run_webchanges_command(workspace=workspace, new_target_ids=new_target_ids)


@app.function
@task(retries=2, retry_delay_seconds=30)
def parse_webchanges_output(
    command_result: CommandResult,
    enabled_target_ids: list[str],
    baseline_target_ids: list[str],
    target_metadata_by_id: dict[str, dict[str, str]],
) -> ParsedMonitorReport:
    """Parse webchanges output and enrich events from config metadata."""
    changed_jobs_payload = None
    if command_result.changed_jobs_path.exists():
        payload = command_result.changed_jobs_path.read_text(encoding="utf-8").strip()
        changed_jobs_payload = payload or None

    raw_report = command_result.stdout or command_result.stderr
    return parse_monitor_report_service(
        raw_report=raw_report,
        changed_jobs_payload=changed_jobs_payload,
        enabled_target_ids=enabled_target_ids,
        baseline_target_ids=baseline_target_ids,
        target_metadata_by_id=target_metadata_by_id,
    )


@app.function
@task(retries=2, retry_delay_seconds=30)
def write_artifacts(
    workspace: WorkspacePaths,
    parsed_report: ParsedMonitorReport,
    raw_report: str,
    run_label: str,
    environment: str,
) -> ArtifactPaths:
    """Write raw and summarized artifacts for the current run."""
    artifact_paths = write_run_artifacts_service(
        workspace_dir=workspace.artifacts_dir,
        raw_report=raw_report,
        parsed_events=[event.model_dump() for event in parsed_report.events],
        run_label=run_label,
    )
    create_markdown_artifact(
        markdown=artifact_paths.changes_markdown_path.read_text(encoding="utf-8"),
        key=f"ir-monitor-summary-{environment}",
        description=f"IR monitor summary for {run_label}",
    )
    return artifact_paths


@app.function
@task(retries=2, retry_delay_seconds=30)
def notify_if_needed(
    config: MonitorConfig,
    parsed_report: ParsedMonitorReport,
    artifact_paths: ArtifactPaths,
    environment: str,
    run_label: str,
    notify_on_no_change: bool | None = None,
) -> NotificationResult:
    """Send content notifications only when needed."""
    return notify_if_needed_service(
        parsed_events=[event.model_dump() for event in parsed_report.events],
        environment=environment,
        run_label=run_label,
        artifact_path=str(artifact_paths.changes_markdown_path),
        webhook_url=SETTINGS.ir_monitor_webhook_url,
        notify_on_no_change=_resolve_notify_on_no_change(
            config=config,
            notify_on_no_change=notify_on_no_change,
        ),
    )


# ============================================================
# FLOW
# ============================================================


@app.function
@flow(name="ir-webchanges-monitor", log_prints=True, on_failure=[notify_on_failure])
def run_ir_webchanges_monitor(
    config_path: str = "./config/ir_monitor/ir_monitor_targets.yaml",
    environment: str = "dev",
    workspace_dir: str | None = None,
    notify_on_no_change: bool | None = None,
    dry_run: bool = False,
) -> dict:
    """Monitor configured IR pages with webchanges and summarize the run."""
    config = load_monitor_config(config_path=config_path)
    workspace = prepare_workspace(
        config=config,
        environment=environment,
        workspace_dir=workspace_dir,
    )
    enabled_target_ids = [target.id for target in config.targets if target.enabled]
    target_metadata_by_id = _target_metadata_by_id(config)
    known_baseline_ids = _load_known_baseline_ids(workspace.baseline_metadata_path)
    new_target_ids = sorted(set(enabled_target_ids) - known_baseline_ids)

    command_result = run_webchanges(
        workspace=workspace,
        new_target_ids=new_target_ids,
        dry_run=dry_run,
    )
    parsed_report = parse_webchanges_output(
        command_result=command_result,
        enabled_target_ids=enabled_target_ids,
        baseline_target_ids=new_target_ids,
        target_metadata_by_id=target_metadata_by_id,
    )
    run_label = datetime.now(ZoneInfo(config.defaults.report_timezone)).isoformat(
        timespec="seconds"
    ).replace(":", "-")
    raw_report = command_result.stdout or command_result.stderr
    artifact_paths = write_artifacts(
        workspace=workspace,
        parsed_report=parsed_report,
        raw_report=raw_report,
        run_label=run_label,
        environment=environment,
    )
    _raise_for_failed_webchanges_run(
        command_result=command_result,
        parsed_report=parsed_report,
        artifact_paths=artifact_paths,
    )
    notification_result = notify_if_needed(
        config=config,
        parsed_report=parsed_report,
        artifact_paths=artifact_paths,
        environment=environment,
        run_label=run_label,
        notify_on_no_change=notify_on_no_change,
    )

    return {
        "environment": environment,
        "workspace_dir": str(workspace.root_dir),
        "changed_count": parsed_report.changed_count,
        "unchanged_target_ids": parsed_report.unchanged_target_ids,
        "failed_target_ids": parsed_report.failed_target_ids,
        "baseline_target_ids": parsed_report.baseline_target_ids,
        "artifacts": {
            "raw_report_path": str(artifact_paths.raw_report_path),
            "changes_json_path": str(artifact_paths.changes_json_path),
            "changes_markdown_path": str(artifact_paths.changes_markdown_path),
        },
        "notification": notification_result.model_dump(),
        "events": [event.model_dump() for event in parsed_report.events],
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
    dry_run_toggle = None
    environment_select = None
    notify_toggle = None
    run_button = None
    ui = None

    if mo.app_meta().mode == "edit":
        config_path_input = mo.ui.text(
            value="./config/ir_monitor/ir_monitor_targets.yaml",
            label="Config Path",
            full_width=True,
        )
        environment_select = mo.ui.dropdown(
            options=["dev", "prod"],
            value="dev",
            label="Environment",
        )
        dry_run_toggle = mo.ui.checkbox(label="Dry Run", value=False)
        notify_toggle = mo.ui.checkbox(label="Notify On No Change", value=False)
        run_button = mo.ui.run_button(label="Run IR Monitor")
        ui = mo.vstack(
            [
                config_path_input,
                environment_select,
                dry_run_toggle,
                notify_toggle,
                run_button,
            ]
        )

    ui
    return (
        config_path_input,
        dry_run_toggle,
        environment_select,
        notify_toggle,
        run_button,
    )


@app.cell
def _(
    config_path_input,
    dry_run_toggle,
    environment_select,
    mo,
    notify_toggle,
    run_button,
):
    interactive_result = None

    if mo.app_meta().mode == "edit" and run_button and run_button.value:
        interactive_result = run_ir_webchanges_monitor(
            config_path=config_path_input.value,
            environment=environment_select.value,
            notify_on_no_change=bool(notify_toggle.value),
            dry_run=bool(dry_run_toggle.value),
        )

    return (interactive_result,)


@app.cell
def _(interactive_result, mo):
    preview_view = None

    if mo.app_meta().mode == "edit":
        if interactive_result is None:
            preview_view = mo.md("No manual run has been triggered yet.")
        else:
            preview_view = mo.md(
                f"```json\n{json.dumps(interactive_result['events'], ensure_ascii=False, indent=2)}\n```"
            )

    preview_view
    return


# ============================================================
# SCRIPT EXECUTION (production)
# ============================================================


@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        result = run_ir_webchanges_monitor()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return


if __name__ == "__main__":
    app.run()

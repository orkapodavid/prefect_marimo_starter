# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "prefect>=3.0.0,<4.0.0",
#     "pydantic-settings>=2.0.0",
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup:
    from datetime import datetime
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess

    from prefect import flow, task

    from shared_utils.config import get_settings, resolve_pg_backup_password
    from shared_utils.prefect_notifications import notify_on_failure, notify_on_success
    from shared_utils.shared_utils_postgres_backup import (
        build_backup_artifacts,
        build_pg_dump_command,
        build_pg_isready_command,
        build_pg_restore_list_command,
        calculate_sha256,
        find_backup_files_to_prune,
        get_latest_dump_size_bytes,
    )

    SETTINGS = get_settings()
    FAILURE_HOOKS = [notify_on_failure] if SETTINGS.notification_enabled and SETTINGS.notify_on_failure else []
    COMPLETION_HOOKS = (
        [notify_on_success] if SETTINGS.notification_enabled and SETTINGS.notify_on_success else []
    )


# ============================================================
# TASKS
# ============================================================


@app.function
@task
def resolve_backup_config(
    database: str | None = None,
    backup_dir: str | None = None,
    retention_days: int | None = None,
    compression_level: int | None = None,
) -> dict:
    """Resolve runtime configuration for a PostgreSQL backup."""
    settings = get_settings()

    database_name = database or settings.pg_backup_database
    backup_directory = Path(backup_dir) if backup_dir else settings.pg_backup_output_dir
    artifacts = build_backup_artifacts(
        backup_dir=backup_directory,
        database=database_name,
        now=datetime.now(),
    )

    return {
        "host": settings.pg_backup_host,
        "port": settings.pg_backup_port,
        "user": settings.pg_backup_user,
        "password": resolve_pg_backup_password(settings),
        "database": database_name,
        "backup_dir": backup_directory,
        "retention_days": (
            retention_days if retention_days is not None else settings.pg_backup_retention_days
        ),
        "compression_level": (
            compression_level
            if compression_level is not None
            else settings.pg_backup_compression_level
        ),
        "connect_timeout_seconds": settings.pg_backup_connect_timeout_seconds,
        "timeout_seconds": settings.pg_backup_timeout_seconds,
        "min_free_space_bytes": settings.pg_backup_min_free_space_gb * 1024**3,
        "artifacts": {
            "dump_file": artifacts.dump_file,
            "checksum_file": artifacts.checksum_file,
        },
    }


@app.function
@task
def check_backup_prerequisites(config: dict) -> dict:
    """Validate local tools, target directory, and free space before backup."""
    binaries = {
        binary: shutil.which(binary)
        for binary in ("pg_isready", "pg_dump", "pg_restore")
    }
    missing_binaries = [binary for binary, resolved in binaries.items() if not resolved]
    if missing_binaries:
        missing_names = ", ".join(missing_binaries)
        raise FileNotFoundError(f"Required PostgreSQL utilities are missing: {missing_names}")

    backup_dir = Path(config["backup_dir"])
    backup_dir.mkdir(parents=True, exist_ok=True)

    free_bytes = shutil.disk_usage(backup_dir).free
    try:
        latest_dump_size_bytes = get_latest_dump_size_bytes(backup_dir)
    except FileNotFoundError:
        latest_dump_size_bytes = 0

    required_free_bytes = max(config["min_free_space_bytes"], latest_dump_size_bytes * 2)
    if free_bytes < required_free_bytes:
        raise RuntimeError(
            "Available free disk space is below the required threshold for backup execution."
        )

    print(
        f"Pre-flight checks passed for {config['database']}: "
        f"free_bytes={free_bytes}, required_free_bytes={required_free_bytes}"
    )
    return {
        "available_tools": binaries,
        "free_bytes": free_bytes,
        "required_free_bytes": required_free_bytes,
    }


@app.function
@task
def check_pg_connection(config: dict) -> dict:
    """Check PostgreSQL connectivity with pg_isready."""
    command = build_pg_isready_command(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        database=config["database"],
        timeout_seconds=config["connect_timeout_seconds"],
    )

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=config["connect_timeout_seconds"],
        env={**os.environ, "PGPASSWORD": config["password"]},
    )
    if result.returncode != 0:
        error_message = result.stderr.strip() or result.stdout.strip() or "pg_isready failed"
        raise RuntimeError(error_message)

    print(f"Connectivity check passed for {config['database']}")
    return {
        "reachable": True,
        "command": command,
        "output": result.stdout.strip(),
    }


@app.function
@task
def run_pg_dump(config: dict, dry_run: bool = False) -> dict:
    """Run pg_dump to create a PostgreSQL custom-format dump."""
    dump_file = Path(config["artifacts"]["dump_file"])
    command = build_pg_dump_command(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        database=config["database"],
        dump_file=dump_file,
        compression_level=config["compression_level"],
        timeout_seconds=config["connect_timeout_seconds"],
    )

    if dry_run:
        print(f"Dry run enabled; skipping pg_dump for {config['database']}")
        return {
            "dump_file": str(dump_file),
            "size_bytes": 0,
            "command": command,
        }

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=config["timeout_seconds"],
        env={**os.environ, "PGPASSWORD": config["password"]},
    )
    if result.returncode != 0:
        error_message = result.stderr.strip() or result.stdout.strip() or "pg_dump failed"
        raise RuntimeError(error_message)

    size_bytes = dump_file.stat().st_size if dump_file.exists() else 0
    print(f"Created dump file {dump_file}")
    return {
        "dump_file": str(dump_file),
        "size_bytes": size_bytes,
        "command": command,
    }


@app.function
@task
def verify_dump(config: dict, dump_result: dict, verify_restore: bool = True, dry_run: bool = False) -> dict:
    """Verify a dump with pg_restore -l before retention pruning."""
    dump_file = Path(dump_result["dump_file"])
    if not verify_restore or dry_run:
        return {"verified": False}

    command = build_pg_restore_list_command(dump_file)
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=config["connect_timeout_seconds"],
        env={**os.environ, "PGPASSWORD": config["password"]},
    )
    if result.returncode != 0:
        error_message = result.stderr.strip() or result.stdout.strip() or "pg_restore verification failed"
        raise RuntimeError(error_message)

    print(f"Verified dump file {dump_file}")
    return {"verified": True}


@app.function
@task
def write_checksum(config: dict, dump_result: dict, dry_run: bool = False) -> dict:
    """Write a SHA-256 sidecar file for a dump."""
    dump_file = Path(dump_result["dump_file"])
    checksum_file = Path(config["artifacts"]["checksum_file"])

    if dry_run:
        return {
            "checksum_file": str(checksum_file),
            "sha256": "",
        }

    sha256 = calculate_sha256(dump_file)
    checksum_file.write_text(f"{sha256}  {dump_file.name}\n", encoding="utf-8")
    print(f"Wrote checksum file {checksum_file}")
    return {
        "checksum_file": str(checksum_file),
        "sha256": sha256,
    }


@app.function
@task
def prune_old_backups(config: dict, dry_run: bool = False) -> dict:
    """Prune expired backup artifacts."""
    backup_dir = Path(config["backup_dir"])
    try:
        prune_candidates = find_backup_files_to_prune(
            backup_dir=backup_dir,
            retention_days=config["retention_days"],
            now=datetime.now(),
        )
    except FileNotFoundError:
        prune_candidates = []

    if not dry_run:
        for prune_candidate in prune_candidates:
            prune_candidate.unlink(missing_ok=True)

    return {
        "pruned_files": [str(path) for path in prune_candidates],
        "pruned_file_count": len(prune_candidates),
    }


@app.function
@task
def build_backup_summary(
    config: dict,
    dump_result: dict,
    verify_result: dict,
    checksum_result: dict,
    prune_result: dict,
    started_at: datetime,
    completed_at: datetime,
    dry_run: bool = False,
) -> dict:
    """Build the structured flow summary."""
    return {
        "database": config["database"],
        "backup_dir": str(config["backup_dir"]),
        "dump_file": dump_result["dump_file"],
        "dump_size_bytes": dump_result["size_bytes"],
        "checksum_file": checksum_result["checksum_file"],
        "sha256": checksum_result["sha256"],
        "verified": verify_result["verified"],
        "pruned_files": prune_result["pruned_files"],
        "pruned_file_count": prune_result["pruned_file_count"],
        "dry_run": dry_run,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
    }


# ============================================================
# FLOW
# ============================================================


@app.function
@flow(
    name="pg-backup",
    log_prints=True,
    on_failure=FAILURE_HOOKS,
    on_completion=COMPLETION_HOOKS,
)
def run_pg_backup(
    database: str | None = None,
    backup_dir: str | None = None,
    retention_days: int | None = None,
    compression_level: int | None = None,
    verify_restore: bool = True,
    dry_run: bool = False,
) -> dict:
    """Run a PostgreSQL backup with verification, checksum, and retention pruning."""
    started_at = datetime.now()

    config = resolve_backup_config(
        database=database,
        backup_dir=backup_dir,
        retention_days=retention_days,
        compression_level=compression_level,
    )
    check_backup_prerequisites(config)
    check_pg_connection(config)
    dump_result = run_pg_dump(config, dry_run=True) if dry_run else run_pg_dump(config)
    verify_result = verify_dump(
        config,
        dump_result,
        verify_restore=verify_restore,
        dry_run=dry_run,
    )
    checksum_result = write_checksum(config, dump_result, dry_run=dry_run)
    prune_result = prune_old_backups(config, dry_run=dry_run)

    return build_backup_summary(
        config,
        dump_result,
        verify_result,
        checksum_result,
        prune_result,
        started_at,
        datetime.now(),
        dry_run,
    )


# ============================================================
# INTERACTIVE CELLS (edit mode only)
# ============================================================


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    database_input = None
    backup_dir_input = None
    retention_days_input = None
    compression_level_input = None
    dry_run_toggle = None
    run_button = None
    ui = None

    if mo.app_meta().mode == "edit":
        settings = get_settings()
        database_input = mo.ui.text(value=settings.pg_backup_database, label="Database")
        backup_dir_input = mo.ui.text(
            value=str(settings.pg_backup_output_dir),
            label="Backup Directory",
            full_width=True,
        )
        retention_days_input = mo.ui.number(
            value=settings.pg_backup_retention_days,
            start=1,
            stop=365,
            label="Retention Days",
        )
        compression_level_input = mo.ui.slider(
            start=0,
            stop=9,
            step=1,
            value=settings.pg_backup_compression_level,
            label="Compression Level",
        )
        dry_run_toggle = mo.ui.checkbox(label="Dry Run", value=False)
        run_button = mo.ui.run_button(label="Run PostgreSQL Backup")

        ui = mo.vstack(
            [
                database_input,
                backup_dir_input,
                retention_days_input,
                compression_level_input,
                dry_run_toggle,
                run_button,
            ]
        )

    ui
    return (
        backup_dir_input,
        compression_level_input,
        database_input,
        dry_run_toggle,
        retention_days_input,
        run_button,
    )


@app.cell
def _(
    backup_dir_input,
    compression_level_input,
    database_input,
    dry_run_toggle,
    mo,
    retention_days_input,
    run_button,
):
    interactive_result = None

    if mo.app_meta().mode == "edit" and run_button and run_button.value:
        interactive_result = run_pg_backup(
            database=database_input.value,
            backup_dir=backup_dir_input.value,
            retention_days=int(retention_days_input.value),
            compression_level=int(compression_level_input.value),
            dry_run=bool(dry_run_toggle.value),
        )

    return (interactive_result,)


@app.cell
def _(backup_dir_input, interactive_result, mo):
    summary_view = None

    if mo.app_meta().mode == "edit":
        recent_rows: list[dict] = []
        backup_dir = (
            Path(backup_dir_input.value)
            if backup_dir_input
            else get_settings().pg_backup_output_dir
        )
        if backup_dir.exists():
            for dump_file in sorted(backup_dir.glob("*.dump"), reverse=True)[:5]:
                dump_stat = dump_file.stat()
                recent_rows.append(
                    {
                        "file": dump_file.name,
                        "size_bytes": dump_stat.st_size,
                        "modified_at": datetime.fromtimestamp(dump_stat.st_mtime).isoformat(
                            timespec="seconds"
                        ),
                    }
                )

        summary_markdown = mo.md(
            "No manual backup run has been triggered yet."
            if interactive_result is None
            else f"```json\n{json.dumps(interactive_result, indent=2)}\n```"
        )
        recent_table = mo.ui.table(recent_rows) if recent_rows else mo.md("No backup files found.")
        summary_view = mo.vstack([summary_markdown, recent_table])

    summary_view
    return


# ============================================================
# SCRIPT EXECUTION (production)
# ============================================================


@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        result = run_pg_backup()
        print(f"Flow Result: {result}")
    return


if __name__ == "__main__":
    app.run()

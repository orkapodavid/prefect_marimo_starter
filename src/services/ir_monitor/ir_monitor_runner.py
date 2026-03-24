"""Subprocess runner for executing webchanges monitor jobs."""

import json
from pathlib import Path
import shutil
import subprocess

from services.ir_monitor.ir_monitor_models import CommandResult, WorkspacePaths


def _webchanges_binary() -> str:
    return shutil.which("webchanges") or "webchanges"


def _build_command(workspace: WorkspacePaths, extra_args: list[str] | None = None) -> list[str]:
    command = [
        _webchanges_binary(),
        "--jobs",
        str(workspace.jobs_path),
        "--config",
        str(workspace.config_path),
        "--database",
        str(workspace.state_dir / "snapshots.db"),
    ]
    if extra_args:
        command.extend(extra_args)
    return command


def _write_baseline_metadata(path: Path, new_target_ids: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"baseline_target_ids": new_target_ids}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_webchanges_command(workspace: WorkspacePaths, new_target_ids: list[str]) -> CommandResult:
    """Run webchanges, preparing new jobs before the main pass when needed."""
    workspace.changed_jobs_path.parent.mkdir(parents=True, exist_ok=True)
    workspace.changed_jobs_path.write_text("", encoding="utf-8")

    if new_target_ids:
        prepare_result = subprocess.run(
            _build_command(workspace, ["--prepare-jobs"]),
            check=False,
            capture_output=True,
            text=True,
        )
        _write_baseline_metadata(workspace.baseline_metadata_path, new_target_ids)
        if prepare_result.returncode != 0:
            return CommandResult(
                exit_code=prepare_result.returncode,
                stdout=prepare_result.stdout,
                stderr=prepare_result.stderr,
                changed_jobs_path=workspace.changed_jobs_path,
                baseline_target_ids=new_target_ids,
            )

    result = subprocess.run(
        _build_command(workspace),
        check=False,
        capture_output=True,
        text=True,
    )
    return CommandResult(
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        changed_jobs_path=workspace.changed_jobs_path,
        baseline_target_ids=new_target_ids,
    )

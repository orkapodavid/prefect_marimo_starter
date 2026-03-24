"""Workspace and jobs builder for IR monitor webchanges runs."""

from collections import Counter
from pathlib import Path
import subprocess
import sys

import yaml

from services.ir_monitor.ir_monitor_models import MonitorConfig, MonitorTarget, WorkspacePaths


def _effective_job_url(target: MonitorTarget, duplicate_count: int) -> str:
    if duplicate_count <= 1:
        return target.page_url

    separator = "&" if "#" in target.page_url else "#"
    return f"{target.page_url}{separator}target_id={target.id}"


def _normalizer_command(target: MonitorTarget) -> str:
    script_path = Path("scripts/ir_monitor/ir_monitor_normalize_content.py").resolve()
    return subprocess.list2cmdline(
        [
            sys.executable,
            str(script_path),
            "--normalizer",
            target.normalizer,
            "--page-url",
            target.page_url,
        ]
    )


def _build_job(target: MonitorTarget, duplicate_count: int) -> dict:
    job = {
        "name": target.id,
        "url": _effective_job_url(target, duplicate_count),
        "user_visible_url": target.user_visible_url,
        "filters": [{"execute": _normalizer_command(target)}],
    }

    if target.use_browser:
        job["use_browser"] = True

    if target.diff_mode == "additions_only":
        job["additions_only"] = True
    else:
        job["differ"] = "unified"

    return job


def build_workspace_files(config: MonitorConfig, workspace_dir: Path) -> WorkspacePaths:
    """Create workspace directories and write generated webchanges files."""
    root_dir = workspace_dir
    generated_dir = root_dir / "generated"
    state_dir = root_dir / "state"
    artifacts_dir = root_dir / "artifacts"
    logs_dir = root_dir / "logs"
    for directory in (
        root_dir / "webchanges",
        generated_dir,
        artifacts_dir,
        logs_dir,
        state_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    workspace = WorkspacePaths(
        root_dir=root_dir,
        generated_dir=generated_dir,
        jobs_path=generated_dir / "jobs.yaml",
        config_path=generated_dir / "config.yaml",
        state_dir=state_dir,
        artifacts_dir=artifacts_dir,
        logs_dir=logs_dir,
        changed_jobs_path=artifacts_dir / "changed_jobs.json",
        baseline_metadata_path=state_dir / "baselines.json",
    )

    enabled_targets = [target for target in config.targets if target.enabled]
    duplicate_counts = Counter(target.page_url for target in enabled_targets)
    jobs_payload = [
        _build_job(target, duplicate_counts[target.page_url]) for target in enabled_targets
    ]
    workspace.jobs_path.write_text(
        yaml.safe_dump_all(jobs_payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    config_payload = {
        "display": {
            "new": False,
            "error": True,
            "unchanged": False,
        },
        "report": {
            "tz": config.defaults.report_timezone,
            "text": {
                "details": True,
                "footer": False,
                "minimal": False,
                "separate": False,
            },
            "stdout": {
                "enabled": True,
            },
        },
    }
    workspace.config_path.write_text(
        yaml.safe_dump(config_payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    if not workspace.baseline_metadata_path.exists():
        workspace.baseline_metadata_path.write_text("{}", encoding="utf-8")

    return workspace

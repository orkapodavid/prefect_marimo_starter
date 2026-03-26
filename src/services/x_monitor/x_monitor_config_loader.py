"""Load and validate X monitor YAML configuration."""

from pathlib import Path

import yaml

from services.x_monitor.x_monitor_models import XMonitorConfig
from shared_utils.paths import resolve_required_repo_file


def load_x_monitor_config(config_path: Path) -> XMonitorConfig:
    """Read, merge defaults, and validate the X monitor configuration."""
    resolved_config_path = resolve_required_repo_file(
        config_path,
        description="X monitor config",
        example_path="config/x_monitor/x_monitor_targets.example.yaml",
    )
    payload = yaml.safe_load(resolved_config_path.read_text(encoding="utf-8")) or {}
    defaults = dict(payload.get("defaults", {}))
    runtime = dict(payload.get("runtime", {}))
    targets = payload.get("targets", [])

    merged_targets = [{**defaults, **target} for target in targets]

    return XMonitorConfig.model_validate(
        {
            "runtime": runtime,
            "defaults": defaults,
            "targets": merged_targets,
        }
    )

"""Load and validate X monitor YAML configuration."""

from pathlib import Path

import yaml

from services.x_monitor.x_monitor_models import XMonitorConfig


def load_x_monitor_config(config_path: Path) -> XMonitorConfig:
    """Read, merge defaults, and validate the X monitor configuration."""
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
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


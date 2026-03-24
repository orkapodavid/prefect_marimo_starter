"""Load and validate IR monitor YAML configuration."""

from pathlib import Path

import yaml

from services.ir_monitor.ir_monitor_models import MonitorConfig


def load_monitor_config(config_path: Path) -> MonitorConfig:
    """Read, merge defaults, and validate the monitor configuration."""
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    defaults = payload.get("defaults", {})
    targets = payload.get("targets", [])

    merged_targets = [{**defaults, **target} for target in targets]

    return MonitorConfig.model_validate(
        {
            "defaults": defaults,
            "targets": merged_targets,
        }
    )

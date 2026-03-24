"""Load and validate IR monitor YAML configuration."""

from pathlib import Path

import yaml

from services.ir_monitor.ir_monitor_models import CompanyEntry, MonitorConfig

LEGACY_RUNTIME_KEYS = {
    "notify_on_no_change",
    "workspace_dir",
    "schedule_cron",
}


def load_monitor_config(config_path: Path) -> MonitorConfig:
    """Read, merge defaults, and validate the monitor configuration."""
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    companies_payload = payload.get("companies", {})
    companies = {
        company_id: CompanyEntry.model_validate(company_payload)
        for company_id, company_payload in companies_payload.items()
    }
    defaults = dict(payload.get("defaults", {}))
    runtime = dict(payload.get("runtime", {}))
    for key in LEGACY_RUNTIME_KEYS:
        if key in defaults and key not in runtime:
            runtime[key] = defaults.pop(key)
        else:
            defaults.pop(key, None)
    targets = payload.get("targets", [])

    merged_targets = []
    for target in targets:
        merged_target = {**defaults, **target}
        company_entry = companies.get(merged_target.get("company_id", ""))
        if company_entry is not None:
            merged_target["company_name"] = company_entry.name
            merged_target["ticker"] = company_entry.ticker
            merged_target["exchange"] = company_entry.exchange
        merged_targets.append(merged_target)

    return MonitorConfig.model_validate(
        {
            "companies": companies,
            "runtime": runtime,
            "defaults": defaults,
            "targets": merged_targets,
        }
    )

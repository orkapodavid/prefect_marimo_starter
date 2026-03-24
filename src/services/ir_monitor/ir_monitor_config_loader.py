"""Load and validate IR monitor YAML configuration."""

from pathlib import Path

import yaml

from services.ir_monitor.ir_monitor_models import CompanyEntry, MonitorConfig


def load_monitor_config(config_path: Path) -> MonitorConfig:
    """Read, merge defaults, and validate the monitor configuration."""
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    companies_payload = payload.get("companies", {})
    companies = {
        company_id: CompanyEntry.model_validate(company_payload)
        for company_id, company_payload in companies_payload.items()
    }
    defaults = payload.get("defaults", {})
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
            "defaults": defaults,
            "targets": merged_targets,
        }
    )

"""Load and validate financial monitor YAML configuration."""

from pathlib import Path

import yaml

from services.financial_monitor.financial_monitor_models import (
    FinancialMonitorCompany,
    FinancialMonitorConfig,
)


def load_financial_monitor_config(config_path: Path) -> FinancialMonitorConfig:
    """Read, merge defaults, and validate the financial monitor configuration."""
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    companies_payload = payload.get("companies", {})
    companies = {
        company_id: FinancialMonitorCompany.model_validate(company_payload)
        for company_id, company_payload in companies_payload.items()
    }
    defaults = dict(payload.get("defaults", {}))
    runtime = dict(payload.get("runtime", {}))
    targets = payload.get("targets", [])

    merged_targets = []
    for target in targets:
        merged_target = {**defaults, **target}
        company_entry = companies.get(merged_target.get("company_id", ""))
        if company_entry is not None:
            merged_target["company_name"] = company_entry.name
            merged_target["ticker"] = company_entry.ticker
            merged_target["exchange"] = company_entry.exchange
            merged_target["edinet_code"] = company_entry.edinet_code
        merged_targets.append(merged_target)

    return FinancialMonitorConfig.model_validate(
        {
            "companies": companies,
            "runtime": runtime,
            "defaults": defaults,
            "targets": merged_targets,
        }
    )

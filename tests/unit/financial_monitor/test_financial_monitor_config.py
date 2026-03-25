from pathlib import Path

from services.financial_monitor.financial_monitor_config import load_financial_monitor_config


def test_load_financial_monitor_config_merges_runtime_and_company_metadata(
    tmp_path: Path,
):
    config_path = tmp_path / "financial_monitor_targets.yaml"
    config_path.write_text(
        """
companies:
  mitsubishi_corp:
    name: Mitsubishi Corporation
    ticker: 8058.T
    exchange: TSE
    edinet_code: E02529
runtime:
  workspace_dir: ./data/financial_monitor/prod
defaults:
  timezone: Asia/Tokyo
  runway_threshold_months: 12
targets:
  - id: mitsubishi_corp_results
    company_id: mitsubishi_corp
    tdnet_language: japanese
    disclosure_keywords: [決算短信]
    include_edinet: true
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_financial_monitor_config(config_path)

    assert config.runtime.workspace_dir.name == "prod"
    assert config.targets[0].company_name == "Mitsubishi Corporation"
    assert config.targets[0].ticker == "8058.T"
    assert config.targets[0].edinet_code == "E02529"

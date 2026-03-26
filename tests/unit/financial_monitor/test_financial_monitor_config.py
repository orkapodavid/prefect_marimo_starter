from pathlib import Path

from services.financial_monitor.financial_monitor_config import load_financial_monitor_config
from shared_utils.paths import get_repo_root


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


def test_load_financial_monitor_config_resolves_repo_relative_example_path_outside_repo_cwd(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    config = load_financial_monitor_config(
        Path("./config/financial_monitor/financial_monitor_targets.example.yaml")
    )

    assert config.runtime.workspace_dir == get_repo_root() / "data/financial_monitor/prod"
    assert config.targets[0].company_name == "Mitsubishi Corporation"

from pathlib import Path

import pytest

from src.services.ir_monitor.ir_monitor_config_loader import load_monitor_config
from src.shared_utils.paths import get_repo_root


def test_load_monitor_config_applies_target_defaults(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
defaults:
  timezone: Asia/Tokyo
  report_timezone: Asia/Tokyo
targets:
  - id: mitsubishi_corp_ir_ja
    company_id: mitsubishi_corp
    company_name: Mitsubishi Corporation
    page_label: Japanese IR page
    page_url: https://example.com/ir
    user_visible_url: https://example.com/ir
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_jp_ir_news
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_monitor_config(config_path)

    assert config.targets[0].country == "JP"
    assert config.targets[0].language == "ja"
    assert config.targets[0].diff_mode == "additions_only"


def test_load_monitor_config_rejects_duplicate_target_ids(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
targets:
  - id: duplicate_id
    company_id: company_a
    company_name: Company A
    page_label: Page A
    page_url: https://example.com/a
    user_visible_url: https://example.com/a
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_jp_ir_news
    enabled: true
  - id: duplicate_id
    company_id: company_b
    company_name: Company B
    page_label: Page B
    page_url: https://example.com/b
    user_visible_url: https://example.com/b
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_jp_ir_news
    enabled: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_monitor_config(config_path)


def test_load_monitor_config_resolves_company_registry_metadata_onto_targets(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
companies:
  mitsubishi_corp:
    name: Mitsubishi Corporation
    ticker: 8058.T
    exchange: TSE
defaults:
  timezone: Asia/Tokyo
  report_timezone: Asia/Tokyo
targets:
  - id: mitsubishi_corp_ir_ja
    company_id: mitsubishi_corp
    page_label: Japanese IR page
    page_url: https://example.com/ir
    user_visible_url: https://example.com/ir
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_jp_ir_news
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_monitor_config(config_path)

    assert config.companies["mitsubishi_corp"].name == "Mitsubishi Corporation"
    assert config.targets[0].company_name == "Mitsubishi Corporation"
    assert config.targets[0].ticker == "8058.T"
    assert config.targets[0].exchange == "TSE"


def test_load_monitor_config_keeps_target_company_name_without_company_registry(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
targets:
  - id: stellapharm_news_en
    company_id: stellapharm
    company_name: Stella Pharma
    page_label: All Stella News
    page_url: https://example.com/news
    user_visible_url: https://example.com/news
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_en_ir_news
    language: en
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_monitor_config(config_path)

    assert config.targets[0].company_name == "Stella Pharma"
    assert config.targets[0].ticker == ""
    assert config.targets[0].exchange == ""


def test_load_monitor_config_company_registry_overrides_conflicting_target_company_name(
    tmp_path: Path,
):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
companies:
  stellapharm:
    name: Stella Pharma
    ticker: STLA.VN
    exchange: HOSE
targets:
  - id: stellapharm_news_en
    company_id: stellapharm
    company_name: Old Company Name
    page_label: All Stella News
    page_url: https://example.com/news
    user_visible_url: https://example.com/news
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_en_ir_news
    language: en
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_monitor_config(config_path)

    assert config.targets[0].company_name == "Stella Pharma"
    assert config.targets[0].ticker == "STLA.VN"
    assert config.targets[0].exchange == "HOSE"


def test_load_monitor_config_requires_company_name_when_company_registry_missing(
    tmp_path: Path,
):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
targets:
  - id: unnamed_target
    company_id: unnamed_company
    page_label: Missing company name
    page_url: https://example.com/news
    user_visible_url: https://example.com/news
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_en_ir_news
    language: en
    enabled: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="company_name"):
        load_monitor_config(config_path)


def test_load_monitor_config_reads_runtime_section_without_merging_into_targets(
    tmp_path: Path,
):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
runtime:
  notify_on_no_change: true
  workspace_dir: ./data/ir_monitor/staging
  schedule_cron: "0 * * * 1-5"
defaults:
  timezone: Asia/Tokyo
targets:
  - id: mitsubishi_corp_ir_ja
    company_id: mitsubishi_corp
    company_name: Mitsubishi Corporation
    page_label: Japanese IR page
    page_url: https://example.com/ir
    user_visible_url: https://example.com/ir
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_jp_ir_news
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_monitor_config(config_path)

    assert config.runtime.notify_on_no_change is True
    assert config.runtime.workspace_dir == get_repo_root() / "data/ir_monitor/staging"
    assert config.runtime.schedule_cron == "0 * * * 1-5"
    assert not hasattr(config.targets[0], "notify_on_no_change")


def test_load_monitor_config_normalizes_legacy_runtime_keys_from_defaults(
    tmp_path: Path,
):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
defaults:
  timezone: Asia/Tokyo
  notify_on_no_change: true
  workspace_dir: ./data/ir_monitor/legacy
targets:
  - id: legacy_target
    company_id: legacy_company
    company_name: Legacy Company
    page_label: Legacy page
    page_url: https://example.com/legacy
    user_visible_url: https://example.com/legacy
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_en_ir_news
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_monitor_config(config_path)

    assert config.runtime.notify_on_no_change is True
    assert config.runtime.workspace_dir == get_repo_root() / "data/ir_monitor/legacy"
    assert config.targets[0].timezone == "Asia/Tokyo"


def test_load_monitor_config_resolves_repo_relative_example_path_outside_repo_cwd(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    config = load_monitor_config(Path("./config/ir_monitor/ir_monitor_targets.example.yaml"))

    assert config.runtime.workspace_dir == get_repo_root() / "data/ir_monitor/prod"
    assert config.targets[0].company_name == "Mitsubishi Corporation"


def test_load_monitor_config_defaults_selector_type_for_normalizer_targets(
    tmp_path: Path,
):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
targets:
  - id: mitsubishi_corp_ir_ja
    company_id: mitsubishi_corp
    company_name: Mitsubishi Corporation
    page_label: Japanese IR page
    page_url: https://example.com/ir
    user_visible_url: https://example.com/ir
    target_kind: html_list
    normalizer: generic_jp_ir_news
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_monitor_config(config_path)

    assert config.targets[0].selector_type == "custom_script"
    assert config.targets[0].selector == ""


def test_load_monitor_config_rejects_unsupported_selector_type(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
targets:
  - id: invalid_selector
    company_id: invalid_company
    company_name: Invalid Company
    page_label: Invalid selector
    page_url: https://example.com/invalid
    user_visible_url: https://example.com/invalid
    target_kind: html_list
    selector_type: css
    normalizer: generic_en_ir_news
    enabled: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="selector_type"):
        load_monitor_config(config_path)

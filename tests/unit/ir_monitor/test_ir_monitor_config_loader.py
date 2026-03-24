from pathlib import Path

import pytest

from src.services.ir_monitor.ir_monitor_config_loader import load_monitor_config


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

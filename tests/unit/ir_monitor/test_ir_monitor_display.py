import pytest

from src.services.ir_monitor import CompanyEntry
from src.services.ir_monitor.ir_monitor_display import (
    company_display_name,
    group_events_by_company,
)
from src.services.ir_monitor.ir_monitor_models import MonitorConfig, MonitorTarget


def test_company_display_name_includes_ticker_when_present():
    assert company_display_name("Mitsubishi Corporation", "8058.T") == (
        "Mitsubishi Corporation (8058.T)"
    )


def test_company_display_name_omits_parentheses_when_ticker_missing():
    assert company_display_name("NAGASE & Co., Ltd.", "") == "NAGASE & Co., Ltd."


def test_group_events_by_company_uses_shared_display_label():
    grouped_events = group_events_by_company(
        [
            {
                "company_name": "Mitsubishi Corporation",
                "ticker": "8058.T",
                "target_id": "mitsubishi_corp_ir_ja",
            },
            {
                "company_name": "Mitsubishi Corporation",
                "ticker": "8058.T",
                "target_id": "mitsubishi_corp_ir_en",
            },
            {
                "company_name": "NAGASE & Co., Ltd.",
                "ticker": "",
                "target_id": "nagase_ir_en",
            },
        ]
    )

    assert list(grouped_events) == [
        "Mitsubishi Corporation (8058.T)",
        "NAGASE & Co., Ltd.",
    ]
    assert [event["target_id"] for event in grouped_events["Mitsubishi Corporation (8058.T)"]] == [
        "mitsubishi_corp_ir_ja",
        "mitsubishi_corp_ir_en",
    ]


def test_ir_monitor_package_exports_company_entry():
    entry = CompanyEntry(name="Mitsubishi Corporation", ticker="8058.T", exchange="TSE")

    assert entry.ticker == "8058.T"


def test_monitor_config_rejects_target_without_resolved_company_name():
    with pytest.raises(ValueError):
        MonitorConfig(
            targets=[
                MonitorTarget(
                    id="broken_target",
                    company_id="broken_company",
                    page_label="Broken page",
                    page_url="https://example.com/broken",
                    user_visible_url="https://example.com/broken",
                    target_kind="html_list",
                    selector_type="custom_script",
                    normalizer="generic_en_ir_news",
                    enabled=True,
                )
            ]
        )

import pytest

from src.services.ir_monitor import CompanyEntry
from src.services.ir_monitor.ir_monitor_display import company_display_name
from src.services.ir_monitor.ir_monitor_models import MonitorConfig, MonitorTarget


def test_company_display_name_includes_ticker_when_present():
    assert company_display_name("Mitsubishi Corporation", "8058.T") == (
        "Mitsubishi Corporation (8058.T)"
    )


def test_company_display_name_omits_parentheses_when_ticker_missing():
    assert company_display_name("NAGASE & Co., Ltd.", "") == "NAGASE & Co., Ltd."


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

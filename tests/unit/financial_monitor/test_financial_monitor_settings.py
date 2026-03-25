from pathlib import Path

from src.shared_utils.config import get_settings


def test_financial_monitor_settings_defaults():
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.financial_monitor_database_url == "postgresql://localhost:5432/workflow_app"
    assert settings.financial_monitor_config_path == Path(
        "./config/financial_monitor/financial_monitor_targets.yaml"
    )
    assert settings.financial_monitor_workspace_dir == Path("./data/financial_monitor")
    assert settings.financial_monitor_reports_dir == Path("./reports/financial_monitor")
    assert settings.financial_monitor_schedule_cron == "0 21 * * 1-5"
    assert settings.financial_monitor_timezone == "Asia/Tokyo"
    assert settings.financial_monitor_report_timezone == "Asia/Tokyo"
    assert settings.financial_monitor_default_runway_threshold_months == 12
    assert settings.financial_monitor_enable_transcripts is False
    assert (
        settings.financial_monitor_edinet_api_key_block_name
        == "financial-monitor-edinet-api-key"
    )

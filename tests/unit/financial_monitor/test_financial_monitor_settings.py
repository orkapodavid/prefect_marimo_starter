from src.shared_utils.config import get_settings
from src.shared_utils.paths import get_repo_root


def test_financial_monitor_settings_defaults():
    get_settings.cache_clear()
    settings = get_settings()
    repo_root = get_repo_root()

    assert settings.financial_monitor_database_url == "postgresql://localhost:5432/workflow_app"
    assert settings.financial_monitor_config_path == (
        repo_root / "config/financial_monitor/financial_monitor_targets.yaml"
    )
    assert settings.financial_monitor_workspace_dir == repo_root / "data/financial_monitor"
    assert settings.financial_monitor_reports_dir == repo_root / "reports/financial_monitor"
    assert settings.financial_monitor_schedule_cron == "0 21 * * 1-5"
    assert settings.financial_monitor_timezone == "Asia/Tokyo"
    assert settings.financial_monitor_report_timezone == "Asia/Tokyo"
    assert settings.financial_monitor_default_runway_threshold_months == 12
    assert settings.financial_monitor_enable_transcripts is False
    assert (
        settings.financial_monitor_edinet_api_key_block_name
        == "financial-monitor-edinet-api-key"
    )

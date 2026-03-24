from src.shared_utils.config import get_settings


def test_ir_monitor_settings_defaults():
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.ir_monitor_workspace_dir.name == "ir_monitor"
    assert settings.ir_monitor_schedule_cron == "0 * * * 1-5"
    assert settings.ir_monitor_timezone == "Asia/Tokyo"
    assert settings.ir_monitor_report_timezone == "Asia/Tokyo"

from src.shared_utils.config import get_settings
from src.shared_utils.paths import get_repo_root


def test_ir_monitor_settings_defaults():
    get_settings.cache_clear()
    settings = get_settings()
    repo_root = get_repo_root()

    assert settings.ir_monitor_config_path == repo_root / "config/ir_monitor/ir_monitor_targets.yaml"
    assert settings.ir_monitor_workspace_dir == repo_root / "data/ir_monitor"
    assert settings.ir_monitor_schedule_cron == "0 * * * 1-5"
    assert settings.ir_monitor_timezone == "Asia/Tokyo"
    assert settings.ir_monitor_report_timezone == "Asia/Tokyo"

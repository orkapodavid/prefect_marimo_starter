from src.shared_utils.config import get_settings
from src.shared_utils.paths import get_repo_root


def test_x_monitor_settings_defaults(monkeypatch):
    monkeypatch.setenv("X_MONITOR_OPERATOR_EMAILS", "")
    get_settings.cache_clear()
    settings = get_settings()
    repo_root = get_repo_root()

    assert settings.x_monitor_database_url == "postgresql://localhost:5432/x_monitor"
    assert settings.x_monitor_config_path == repo_root / "config/x_monitor/x_monitor_targets.yaml"
    assert settings.x_monitor_workspace_dir == repo_root / "data/x_monitor"
    assert settings.x_monitor_twscrape_accounts_db == (
        repo_root / "data/x_monitor/twscrape/accounts.db"
    )
    assert settings.x_monitor_gmail_provider == "gmail_smtp"
    assert settings.x_monitor_gmail_api_use_adc is False
    assert settings.x_monitor_poll_cron == "*/5 * * * *"
    assert settings.x_monitor_digest_cron == "0 8 * * *"
    assert settings.x_monitor_health_cron == "*/30 * * * *"
    assert settings.x_monitor_timezone == "Asia/Singapore"
    assert settings.x_monitor_poll_batch_limit == 25
    assert settings.x_monitor_immediate_alerts_enabled is True
    assert settings.x_monitor_daily_digest_enabled is True
    assert settings.x_monitor_subject_prefix == "[X Monitor]"
    assert settings.x_monitor_operator_emails == ""
    assert settings.x_monitor_consecutive_failure_threshold == 3

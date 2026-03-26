from src.shared_utils.config import Settings, get_settings
from src.shared_utils.paths import get_repo_root


def test_get_settings():
    """Test that settings can be loaded."""
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.environment == "dev"


def test_settings_override(monkeypatch):
    """Test that environment override works."""
    get_settings.cache_clear()
    # Mock environment variable
    # The config.py uses 'ENVIRONMENT' env var (defaulting to 'dev')
    monkeypatch.setenv("ENVIRONMENT", "prod")

    settings = get_settings()
    assert settings.environment == "prod"
    get_settings.cache_clear()


def test_settings_ignore_unknown_dotenv_entries(tmp_path):
    """Unknown keys in a local .env should not break settings loading."""
    env_file = tmp_path / ".env"
    env_file.write_text("ENVIRONMENT=dev\nEDINET_API_KEY=dotenv-key\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.environment == "dev"


def test_get_settings_resolves_repo_relative_paths_from_repo_root():
    get_settings.cache_clear()

    settings = get_settings()
    repo_root = get_repo_root()

    assert settings.data_directory == repo_root / "data"
    assert settings.log_directory == repo_root / "logs"
    assert settings.reports_directory == repo_root / "reports"
    assert settings.ir_monitor_config_path == repo_root / "config/ir_monitor/ir_monitor_targets.yaml"
    assert (
        settings.financial_monitor_config_path
        == repo_root / "config/financial_monitor/financial_monitor_targets.yaml"
    )
    assert settings.x_monitor_config_path == repo_root / "config/x_monitor/x_monitor_targets.yaml"
    assert settings.data_directory.is_absolute()
    assert settings.financial_monitor_reports_dir.is_absolute()
    assert settings.x_monitor_twscrape_accounts_db.is_absolute()

from src.shared_utils.config import Settings, get_settings


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

from src.shared_utils.config import get_settings


def test_get_settings():
    """Test that settings can be loaded."""
    settings = get_settings()
    assert settings.environment == "dev"


def test_settings_override(monkeypatch):
    """Test that environment override works."""
    # Mock environment variable
    # The config.py uses 'ENVIRONMENT' env var (defaulting to 'dev')
    monkeypatch.setenv("ENVIRONMENT", "prod")

    settings = get_settings()
    assert settings.environment == "prod"

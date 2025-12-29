from workflow_utils.config import get_settings, reset_settings


def test_get_settings():
    """Test that settings can be loaded."""
    settings = get_settings()
    assert settings.app_name == "Prefect Marimo Workflows"
    assert settings.environment == "dev"


def test_settings_override():
    """Test that environment override works."""
    reset_settings()
    settings = get_settings(env="prod")
    assert settings.environment == "prod"

import pytest

from workflow_utils.config import Settings


@pytest.fixture
def test_settings():
    """Provides a settings object for testing."""
    return Settings(environment="dev", database_url="sqlite:///:memory:", app_name="Test Workflow")


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mocks environment variables for tests."""
    monkeypatch.setenv("PREFECT_API_URL", "http://localhost:4200/api")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

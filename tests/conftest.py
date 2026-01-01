import os
import pytest
from pathlib import Path
import tempfile
import shutil

from src.shared_utils.config import Settings, get_settings


@pytest.fixture
def test_settings():
    """Provides a settings object for testing."""
    return Settings(environment="dev", database_url="sqlite:///:memory:")


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Automatically clear settings cache before each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mocks environment variables for tests."""
    monkeypatch.setenv("PREFECT_API_URL", "http://localhost:4200/api")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def isolated_env(monkeypatch):
    """Provides a clean environment for tests that need to modify env vars.
    
    Usage:
        def test_something(isolated_env):
            isolated_env.setenv("MY_VAR", "value")
            # Test code here
    """
    # Save original environment
    original_env = os.environ.copy()
    
    yield monkeypatch
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_data_dir():
    """Creates a temporary directory structure for file system tests.
    
    Returns:
        Path: Path to temporary directory with data/, logs/, reports/ subdirs
    
    Usage:
        def test_file_operations(temp_data_dir):
            input_path = temp_data_dir / "data" / "input" / "test.parquet"
            # Test code here
    """
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create directory structure
    (temp_dir / "data" / "input").mkdir(parents=True, exist_ok=True)
    (temp_dir / "data" / "output").mkdir(parents=True, exist_ok=True)
    (temp_dir / "data" / "dev" / "input").mkdir(parents=True, exist_ok=True)
    (temp_dir / "data" / "dev" / "output").mkdir(parents=True, exist_ok=True)
    (temp_dir / "logs").mkdir(parents=True, exist_ok=True)
    (temp_dir / "reports").mkdir(parents=True, exist_ok=True)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

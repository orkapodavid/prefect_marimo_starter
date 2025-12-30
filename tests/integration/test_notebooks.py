import os
import pytest
import subprocess


@pytest.fixture(scope="module", autouse=True)
def configure_ephemeral_prefect():
    """Ensure Prefect uses ephemeral mode for integration tests."""
    original = os.environ.get("PREFECT_API_URL")
    os.environ.pop("PREFECT_API_URL", None)
    yield
    if original:
        os.environ["PREFECT_API_URL"] = original


@pytest.mark.integration
def test_extract_data_runs():
    """Test extract_data notebook executes successfully."""
    env = os.environ.copy()
    env.pop("PREFECT_API_URL", None)
    # Ensure PYTHONPATH includes repo root
    env["PYTHONPATH"] = f"{os.getcwd()}:{env.get('PYTHONPATH', '')}"

    result = subprocess.run(
        ["python", "notebooks/etl/extract_data.py"], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, f"Failed: {result.stderr}\nStdout: {result.stdout}"


@pytest.mark.integration
def test_daily_summary_runs():
    """Test daily_summary notebook executes successfully."""
    env = os.environ.copy()
    env.pop("PREFECT_API_URL", None)
    # Ensure PYTHONPATH includes repo root
    env["PYTHONPATH"] = f"{os.getcwd()}:{env.get('PYTHONPATH', '')}"

    result = subprocess.run(
        ["python", "notebooks/reports/daily_summary.py"], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, f"Failed: {result.stderr}\nStdout: {result.stdout}"

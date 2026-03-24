from pathlib import Path

import pytest


@pytest.fixture
def ir_monitor_fixtures_dir() -> Path:
    return Path("tests/fixtures/ir_monitor")

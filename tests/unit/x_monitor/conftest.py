"""Shared pytest fixtures for x_monitor tests."""

import pytest
from sqlalchemy import create_engine

from services.x_monitor.x_monitor_tables import X_MONITOR_METADATA


@pytest.fixture
def in_memory_x_monitor_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    X_MONITOR_METADATA.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


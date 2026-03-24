"""Database helpers for X monitor persistence."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from shared_utils.config import get_settings


def get_x_monitor_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for the X monitor database."""
    resolved_database_url = database_url or get_settings().x_monitor_database_url
    return create_engine(resolved_database_url, future=True)


def get_x_monitor_session(
    engine: Engine | None = None,
    database_url: str | None = None,
) -> sessionmaker[Session]:
    """Create a configured SQLAlchemy session factory."""
    resolved_engine = engine or get_x_monitor_engine(database_url=database_url)
    return sessionmaker(bind=resolved_engine, expire_on_commit=False, future=True)


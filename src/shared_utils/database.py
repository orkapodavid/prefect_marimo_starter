"""Database connection utilities."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.shared_utils.config import get_settings


def get_db_engine():
    """Get database engine."""
    settings = get_settings()
    return create_engine(settings.database_url)


def get_db_session():
    """Get database session."""
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()

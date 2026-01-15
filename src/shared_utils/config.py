"""Configuration management for workflows."""

from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # App Info
    app_name: str = Field(default="Prefect Marimo Workflows")
    app_version: str = Field(default="1.0.0")
    environment: str = Field(default="dev")
    log_level: str = Field(default="INFO")

    # Database
    database_url: str = Field(default="sqlite:///data/workflow.db")
    db_pool_size: int = Field(default=5)

    # Prefect
    prefect_api_url: str | None = Field(default=None)
    work_pool_name: str = Field(default="windows-process-pool")

    # Paths
    data_directory: Path = Field(default=Path("./data"))
    log_directory: Path = Field(default=Path("./logs"))
    reports_directory: Path = Field(default=Path("./reports"))

    # Processing defaults
    batch_size: int = Field(default=1000)
    retry_attempts: int = Field(default=3)
    timeout_seconds: int = Field(default=300)

    # Notifications
    notification_enabled: bool = Field(default=True)
    notification_email: str = Field(default="")
    notify_on_failure: bool = Field(default=True)
    notify_on_success: bool = Field(default=False)

    # Exchange
    exchange_username: str = Field(default="user@company.com")
    exchange_password: str = Field(default="")
    exchange_ews_url: str | None = Field(default=None)

    # MS SQL Dev
    dev_mssql_server: str = Field(default="localhost")
    dev_mssql_database: str = Field(default="dev_db")
    dev_mssql_username: str = Field(default="dev_user")
    dev_mssql_password: str = Field(default="dev_pass")

    # MS SQL Prod
    prod_mssql_server: str = Field(default="prod_server")
    prod_mssql_database: str = Field(default="prod_db")
    prod_mssql_username: str = Field(default="prod_user")
    prod_mssql_password: str = Field(default="prod_pass")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings(environment: str = None) -> Settings:
    """Get settings for specified environment."""
    if environment:
        env_file = Path(f"config/environments/{environment}.env")
        if env_file.exists():
            return Settings(_env_file=env_file)
    return Settings()

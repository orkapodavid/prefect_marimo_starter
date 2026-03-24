"""Configuration management for workflows."""

from functools import lru_cache
import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App Info
    app_name: str = Field(default="Prefect Marimo Workflows")
    app_version: str = Field(default="1.0.0")
    environment: str = Field(default="dev")
    log_level: str = Field(default="INFO")

    # Database
    database_url: str = Field(default="postgresql://localhost:5432/workflow_app")
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

    # PostgreSQL Backup
    pg_backup_host: str = Field(default="localhost")
    pg_backup_port: int = Field(default=5432)
    pg_backup_user: str = Field(default="backup_user")
    pg_backup_password: str = Field(default="")
    pg_backup_password_block_name: str | None = Field(default=None)
    pg_backup_database: str = Field(default="postgres")
    pg_backup_output_dir: Path = Field(default=Path("./data/backups/postgres"))
    pg_backup_retention_days: int = Field(default=30)
    pg_backup_schedule_cron: str = Field(default="0 2 * * *")
    pg_backup_timezone: str = Field(default="Asia/Hong_Kong")
    pg_backup_compression_level: int = Field(default=6)
    pg_backup_connect_timeout_seconds: int = Field(default=15)
    pg_backup_timeout_seconds: int = Field(default=3600)
    pg_backup_min_free_space_gb: int = Field(default=5)

    # IR Monitor
    ir_monitor_workspace_dir: Path = Field(default=Path("./data/ir_monitor"))
    ir_monitor_schedule_cron: str = Field(default="0 * * * 1-5")
    ir_monitor_timezone: str = Field(default="Asia/Tokyo")
    ir_monitor_report_timezone: str = Field(default="Asia/Tokyo")
    ir_monitor_webhook_url: str = Field(default="")

    # X Monitor
    x_monitor_database_url: str = Field(default="postgresql://localhost:5432/x_monitor")
    x_monitor_config_path: Path = Field(
        default=Path("./config/x_monitor/x_monitor_targets.yaml")
    )
    x_monitor_workspace_dir: Path = Field(default=Path("./data/x_monitor"))
    x_monitor_twscrape_accounts_db: Path = Field(
        default=Path("./data/x_monitor/twscrape/accounts.db")
    )
    x_monitor_gmail_provider: str = Field(default="gmail_smtp")
    x_monitor_gmail_smtp_host: str = Field(default="smtp.gmail.com")
    x_monitor_gmail_smtp_port: int = Field(default=587)
    x_monitor_gmail_smtp_username: str = Field(default="")
    x_monitor_gmail_smtp_password: str = Field(default="")
    x_monitor_gmail_smtp_from: str = Field(default="")
    x_monitor_gmail_smtp_use_starttls: bool = Field(default=True)
    x_monitor_gmail_api_credentials_file: str = Field(default="")
    x_monitor_gmail_api_token_file: str = Field(default="")
    x_monitor_gmail_api_from: str = Field(default="")
    x_monitor_gmail_api_use_adc: bool = Field(default=False)
    x_monitor_poll_cron: str = Field(default="*/5 * * * *")
    x_monitor_digest_cron: str = Field(default="0 8 * * *")
    x_monitor_health_cron: str = Field(default="*/30 * * * *")
    x_monitor_timezone: str = Field(default="Asia/Singapore")
    x_monitor_poll_batch_limit: int = Field(default=25)
    x_monitor_immediate_alerts_enabled: bool = Field(default=True)
    x_monitor_daily_digest_enabled: bool = Field(default=True)
    x_monitor_subject_prefix: str = Field(default="[X Monitor]")
    x_monitor_operator_emails: str = Field(default="")
    x_monitor_consecutive_failure_threshold: int = Field(default=3)


def resolve_pg_backup_password(settings: Settings | None = None) -> str:
    """Resolve the PostgreSQL backup password without logging secrets."""
    settings = settings or get_settings()

    if settings.pg_backup_password_block_name:
        from prefect.blocks.system import Secret

        password = Secret.load(settings.pg_backup_password_block_name).get()
        if password:
            return password

    if settings.pg_backup_password:
        return settings.pg_backup_password

    if os.getenv("PG_BACKUP_PASSWORD"):
        return os.environ["PG_BACKUP_PASSWORD"]

    fallback_settings = get_settings()
    if fallback_settings.pg_backup_password:
        return fallback_settings.pg_backup_password

    raise ValueError(
        "PostgreSQL backup password is not configured. Set "
        "`pg_backup_password_block_name` or `PG_BACKUP_PASSWORD`."
    )


@lru_cache
def get_settings(environment: str = None) -> Settings:
    """Get settings for specified environment."""
    if environment:
        env_file = Path(f"config/environments/{environment}.env")
        if env_file.exists():
            return Settings(_env_file=env_file)
    return Settings()

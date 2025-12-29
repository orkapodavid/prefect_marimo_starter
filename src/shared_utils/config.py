"""Configuration management for workflows."""

from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    environment: str = Field(default="dev")
    database_url: str = Field(default="sqlite:///data/workflow.db")
    data_directory: Path = Field(default=Path("./data"))
    log_level: str = Field(default="INFO")
    prefect_api_url: str = Field(default="http://localhost:4200/api")
    
    # Processing defaults
    batch_size: int = Field(default=1000)
    retry_attempts: int = Field(default=3)
    timeout_seconds: int = Field(default=300)

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

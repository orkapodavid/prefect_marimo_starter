# src/services/mssql/mssql_service.py

import pyodbc
import pandas as pd
from pathlib import Path
from prefect import get_run_logger
import yaml
import logging


class MSSQLService:
    """A service for connecting to and querying a Microsoft SQL Server database."""

    def __init__(self, server: str, database: str, username: str, password: str):
        """Initializes the MSSQLService with database credentials."""
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.cnxn = None
        try:
            self.logger = get_run_logger()
        except Exception:
            # Fallback for when running outside of a flow context (e.g., tests/notebooks)
            self.logger = logging.getLogger("MSSQLService")
            # Ensure basic configuration if root logger isn't configured
            if not self.logger.handlers:
                logging.basicConfig(level=logging.INFO)

        self._connect()

    def _connect(self):
        """Establishes a connection to the SQL Server database."""
        if self.cnxn:
            return

        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
        )
        try:
            self.cnxn = pyodbc.connect(conn_str)
            self.logger.info(
                f"Successfully connected to database '{self.database}' on server '{self.server}'."
            )
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise

    def execute_query(self, sql: str, params: list = None) -> pd.DataFrame:
        """Execute SQL query directly without requiring a file.

        Args:
            sql: SQL query string with ? placeholders
            params: Optional list of positional parameters

        Returns:
            DataFrame containing query results

        Example:
            df = service.execute_query(
                "SELECT * FROM Customers WHERE Country = ?",
                params=["USA"]
            )
        """
        self.logger.info("Executing direct SQL query")

        try:
            df = pd.read_sql_query(sql, self.cnxn, params=params if params else None)
            self.logger.info(f"Query executed successfully, returning {len(df)} rows.")
            return df
        except Exception as e:
            self.logger.error(f"Error executing SQL query: {e}")
            raise

    def execute_query_from_file(self, file_path: str, params: list = None) -> pd.DataFrame:
        """Reads a .sql file and executes the query with optional metadata.

        Supports two formats:
        1. Plain SQL files (just SQL query)
        2. Structured files with YAML frontmatter (metadata + SQL)

        Args:
            file_path: Path to the .sql file
            params: Optional list of positional parameters matching ? placeholders in SQL

        Returns:
            DataFrame containing query results
        """
        self.logger.info(f"Executing query from file: {file_path}")

        full_path = Path(file_path)
        if not full_path.exists():
            self.logger.error(f"SQL file not found at path: {file_path}")
            raise FileNotFoundError(f"SQL file not found: {file_path}")

        content = full_path.read_text()

        # Auto-detect file format
        if content.strip().startswith("---"):
            # Structured format with YAML frontmatter
            parts = content.split("---", 2)
            if len(parts) < 3:
                self.logger.error("Invalid SQL file format: incomplete YAML block")
                raise ValueError("Invalid SQL file format.")

            metadata_str, sql_query = parts[1], parts[2]
            metadata = yaml.safe_load(metadata_str)
            description = metadata.get("description", "N/A")
            self.logger.info(f"Query Description: {description}")
        else:
            # Plain SQL format
            sql_query = content
            self.logger.info("Executing plain SQL file (no metadata)")

        return self.execute_query(sql_query, params)

    def __del__(self):
        """Destructor to close the database connection."""
        if self.cnxn:
            try:
                self.cnxn.close()
                self.logger.info("Database connection closed.")
            except Exception:
                pass

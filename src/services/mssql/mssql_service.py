# src/services/mssql/mssql_service.py

import pyodbc
import pandas as pd
from pathlib import Path
from prefect import get_run_logger
import yaml
import logging
import re


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

    def execute_query_from_file(self, file_path: str, params: dict = None) -> pd.DataFrame:
        """Reads a .sql file, parses metadata, and executes the query with parameters."""
        self.logger.info(f"Executing query from file: {file_path}")

        full_path = Path(file_path)
        if not full_path.exists():
            self.logger.error(f"SQL file not found at path: {file_path}")
            raise FileNotFoundError(f"SQL file not found: {file_path}")

        content = full_path.read_text()

        # Parse metadata and SQL query
        parts = content.split("---", 2)
        if len(parts) < 3:
            self.logger.error("SQL file must contain a YAML metadata block.")
            raise ValueError("Invalid SQL file format.")

        metadata_str, sql_query = parts[1], parts[2]
        metadata = yaml.safe_load(metadata_str)
        self.logger.info(f"Query Description: {metadata.get('description', 'N/A')}")

        try:
            # pyodbc uses '?' for positional parameters
            # We need to convert our named parameters (@param) to a positional list
            param_values = []
            if params:
                # Build a single regex pattern for all parameters: @param1|@param2|...
                # Also match single-quoted strings to ignore them: '...'

                # Get all parameter names from metadata that are provided in params
                param_names = [
                    p["name"] for p in metadata.get("parameters", []) if p["name"] in params
                ]

                if param_names:
                    # Sort by length descending to ensure @longer_param is matched before @longer
                    param_names.sort(key=len, reverse=True)

                    # Create regex group for parameters: (@param1\b|@param2\b|...)
                    params_pattern = "|".join([f"@{re.escape(name)}\\b" for name in param_names])

                    # Combined pattern: match strings OR parameters
                    # Group 1: String literal
                    # Group 2: Parameter
                    full_pattern = re.compile(f"('([^']|'')*')|({params_pattern})", re.IGNORECASE)

                    def replacement(match):
                        # If it's a string literal, return it unchanged
                        if match.group(1):
                            return match.group(1)

                        # It's a parameter (e.g. @id)
                        param_match = match.group(2)
                        # param_match is something like "@id"
                        param_key = param_match[1:]  # strip @

                        # Find the correct case-sensitive key from params if needed,
                        # but we matched based on metadata names which we know exist in params.
                        # However, regex might have matched case-insensitively if we used re.IGNORECASE for everything.
                        # But we constructed the regex from exact metadata keys.
                        # To be safe, look it up carefully.

                        # We used re.IGNORECASE, so param_match might be @ID vs @id.
                        # We need to find which key it corresponds to.
                        for name in param_names:
                            if name.lower() == param_key.lower():
                                param_values.append(params[name])
                                return "?"

                        # Should not happen if regex is correct
                        return param_match

                    sql_query = full_pattern.sub(replacement, sql_query)

            df = pd.read_sql_query(
                sql_query, self.cnxn, params=param_values if param_values else None
            )
            self.logger.info(f"Query executed successfully, returning {len(df)} rows.")
            return df
        except Exception as e:
            self.logger.error(f"Error executing query from {file_path}: {e}")
            raise

    def __del__(self):
        """Destructor to close the database connection."""
        if self.cnxn:
            try:
                self.cnxn.close()
                self.logger.info("Database connection closed.")
            except Exception:
                pass

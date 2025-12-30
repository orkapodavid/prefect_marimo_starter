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

    @staticmethod
    def _prepare_query_params(
        sql_query: str, params: dict, metadata_params: list
    ) -> tuple[str, list]:
        """
        Replaces named parameters (e.g. @id) with '?' and builds the positional values list.
        Safely handles SQL string literals.
        """
        param_values = []
        if not params:
            return sql_query, param_values

        # Get all parameter names from metadata that are provided in params
        param_names = [p["name"] for p in metadata_params if p["name"] in params]

        if not param_names:
            return sql_query, param_values

        # Sort by length descending to ensure @longer_param is matched before @longer
        param_names.sort(key=len, reverse=True)

        # Create regex group for parameters: (@param1\b|@param2\b|...)
        params_pattern = "|".join([f"@{re.escape(name)}\\b" for name in param_names])

        # Combined pattern: match strings OR parameters
        # Group 1: String literal '...' (handling escaped quotes '')
        # Group 2: Inner content of string (ignore)
        # Group 3: Parameter match
        full_pattern = re.compile(f"('([^']|'')*')|({params_pattern})", re.IGNORECASE)

        new_query_parts = []
        last_pos = 0

        # Iterate through all matches once
        for match in full_pattern.finditer(sql_query):
            # Append text before match
            new_query_parts.append(sql_query[last_pos : match.start()])

            # Group 1: String literal - keep as is
            if match.group(1):
                new_query_parts.append(match.group(1))

            # Group 3: Parameter match
            elif match.group(3):
                param_match = match.group(3)
                param_key = param_match[1:]  # strip @

                # Identify which parameter it is (case-insensitive lookup logic)
                found = False
                for name in param_names:
                    if name.lower() == param_key.lower():
                        param_values.append(params[name])
                        new_query_parts.append("?")
                        found = True
                        break

                if not found:
                    # Should unlikely happen given regex construction, but keep original if not found
                    new_query_parts.append(param_match)

            last_pos = match.end()

        # Append remaining text
        new_query_parts.append(sql_query[last_pos:])

        return "".join(new_query_parts), param_values

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
            # Use the static method to prepare query and params
            metadata_params = metadata.get("parameters", [])
            final_sql, param_values = self._prepare_query_params(sql_query, params, metadata_params)

            df = pd.read_sql_query(
                final_sql, self.cnxn, params=param_values if param_values else None
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

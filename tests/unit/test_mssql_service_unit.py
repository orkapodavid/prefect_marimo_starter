import sys
from unittest.mock import MagicMock, patch

# Mock pyodbc before importing MSSQLService because libodbc is not available in sandbox
sys.modules["pyodbc"] = MagicMock()

from src.services.mssql.mssql_service import MSSQLService  # noqa: E402


class TestMSSQLServiceExecute:
    @patch("src.services.mssql.mssql_service.pd.read_sql_query")
    @patch("src.services.mssql.mssql_service.Path")
    def test_execute_query_with_params(self, mock_path, mock_read_sql):
        """Test query execution with positional parameters"""
        # Setup mocks
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        # Note: The split('---', 2) will preserve the newline after the second ---
        mock_file.read_text.return_value = (
            "---\ndescription: test\n---\nSELECT * FROM table WHERE id = ?"
        )
        mock_path.return_value = mock_file

        # Mock connection to avoid real DB logic
        with patch.object(MSSQLService, "_connect"):
            service = MSSQLService("server", "db", "user", "pass")
            service.cnxn = MagicMock()

            # Execute
            service.execute_query_from_file("test.sql", params=[123])

            # Assert pd.read_sql_query was called with correct params
            mock_read_sql.assert_called_once()
            args, kwargs = mock_read_sql.call_args

            # Check SQL query passed (args[0]) - expect leading newline
            assert args[0] == "\nSELECT * FROM table WHERE id = ?"

            # Check params passed (kwargs['params'])
            assert kwargs["params"] == [123]

    @patch("src.services.mssql.mssql_service.pd.read_sql_query")
    @patch("src.services.mssql.mssql_service.Path")
    def test_execute_query_no_params(self, mock_path, mock_read_sql):
        """Test query execution with no parameters"""
        # Setup mocks
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = "---\ndescription: test\n---\nSELECT * FROM table"
        mock_path.return_value = mock_file

        # Mock connection
        with patch.object(MSSQLService, "_connect"):
            service = MSSQLService("server", "db", "user", "pass")
            service.cnxn = MagicMock()

            # Execute
            service.execute_query_from_file("test.sql")

            # Assert params is None
            mock_read_sql.assert_called_once()
            args, kwargs = mock_read_sql.call_args
            assert kwargs["params"] is None

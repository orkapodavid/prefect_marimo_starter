import sys
from unittest.mock import MagicMock, patch

# Mock pyodbc before importing MSSQLService because libodbc is not available in sandbox
sys.modules["pyodbc"] = MagicMock()

from src.services.mssql.mssql_service import MSSQLService  # noqa: E402


class TestMSSQLServiceExecute:
    @patch("src.services.mssql.mssql_service.pd.read_sql_query")
    def test_execute_query_direct(self, mock_read_sql):
        """Test direct SQL execution"""
        # Mock connection
        with patch.object(MSSQLService, "_connect"):
            service = MSSQLService("server", "db", "user", "pass")
            service.cnxn = MagicMock()

            # Execute
            service.execute_query("SELECT * FROM table WHERE id = ?", params=[123])

            # Assert
            mock_read_sql.assert_called_once()
            args, kwargs = mock_read_sql.call_args
            assert args[0] == "SELECT * FROM table WHERE id = ?"
            assert kwargs["params"] == [123]

    @patch("src.services.mssql.mssql_service.pd.read_sql_query")
    @patch("src.services.mssql.mssql_service.Path")
    def test_execute_query_from_plain_file(self, mock_path, mock_read_sql):
        """Test plain SQL file without metadata"""
        # Setup mocks
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = "SELECT * FROM table WHERE id = ?"
        mock_path.return_value = mock_file

        # Mock connection
        with patch.object(MSSQLService, "_connect"):
            service = MSSQLService("server", "db", "user", "pass")
            service.cnxn = MagicMock()

            # Execute
            service.execute_query_from_file("test_plain.sql", params=[123])

            # Assert
            mock_read_sql.assert_called_once()
            args, kwargs = mock_read_sql.call_args
            assert args[0] == "SELECT * FROM table WHERE id = ?"
            assert kwargs["params"] == [123]

    @patch("src.services.mssql.mssql_service.pd.read_sql_query")
    @patch("src.services.mssql.mssql_service.Path")
    def test_execute_query_from_structured_file(self, mock_path, mock_read_sql):
        """Test SQL file with YAML metadata"""
        # Setup mocks
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = (
            "---\ndescription: test\n---\nSELECT * FROM table WHERE id = ?"
        )
        mock_path.return_value = mock_file

        # Mock connection
        with patch.object(MSSQLService, "_connect"):
            service = MSSQLService("server", "db", "user", "pass")
            service.cnxn = MagicMock()

            # Execute
            service.execute_query_from_file("test_structured.sql", params=[123])

            # Assert
            mock_read_sql.assert_called_once()
            args, kwargs = mock_read_sql.call_args
            # Note: split matches how it works in service
            assert args[0] == "\nSELECT * FROM table WHERE id = ?"
            assert kwargs["params"] == [123]

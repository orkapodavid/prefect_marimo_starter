import sys
from unittest.mock import MagicMock, patch

# Mock pyodbc before importing MSSQLService because libodbc is not available in sandbox
sys.modules["pyodbc"] = MagicMock()

from src.services.mssql.mssql_service import MSSQLService  # noqa: E402


class TestMSSQLServiceExecute:
    @patch("src.services.mssql.mssql_service.pd.read_sql_query")
    def test_execute_query_direct(self, mock_read_sql):
        """Test direct SQL execution"""
        service = MSSQLService("server", "db", "user", "pass")
        service.cnxn = MagicMock()  # Simulate connected state

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

        service = MSSQLService("server", "db", "user", "pass")
        service.cnxn = MagicMock()  # Simulate connected

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

        service = MSSQLService("server", "db", "user", "pass")
        service.cnxn = MagicMock()  # Simulate connected

        # Execute
        service.execute_query_from_file("test_structured.sql", params=[123])

        # Assert
        mock_read_sql.assert_called_once()
        args, kwargs = mock_read_sql.call_args
        assert args[0] == "\nSELECT * FROM table WHERE id = ?"
        assert kwargs["params"] == [123]


class TestMSSQLServiceConnection:
    def test_lazy_connection(self):
        """Test that connection is not established in __init__"""
        service = MSSQLService("server", "db", "user", "pass")
        assert service.cnxn is None  # Not connected yet

    @patch("src.services.mssql.mssql_service.pyodbc.connect")
    def test_explicit_connect(self, mock_pyodbc_connect):
        """Test explicit connection"""
        service = MSSQLService("server", "db", "user", "pass")
        service.connect()
        assert service.cnxn is not None
        mock_pyodbc_connect.assert_called_once()

        # Test idempotency
        service.connect()
        mock_pyodbc_connect.assert_called_once()  # Should not be called again

    @patch("src.services.mssql.mssql_service.pyodbc.connect")
    def test_disconnect(self, mock_pyodbc_connect):
        """Test explicit disconnect"""
        service = MSSQLService("server", "db", "user", "pass")
        service.connect()
        mock_cnxn = service.cnxn

        service.disconnect()
        assert service.cnxn is None
        mock_cnxn.close.assert_called_once()

    @patch("src.services.mssql.mssql_service.pyodbc.connect")
    def test_context_manager(self, mock_pyodbc_connect):
        """Test context manager protocol"""
        with MSSQLService("server", "db", "user", "pass") as service:
            assert service.cnxn is not None
            mock_pyodbc_connect.assert_called_once()
            # Simulate connection object for cleanup check
            mock_cnxn = MagicMock()
            service.cnxn = mock_cnxn

        # After context exit, should be disconnected
        assert service.cnxn is None
        mock_cnxn.close.assert_called_once()

    @patch("src.services.mssql.mssql_service.pyodbc.connect")
    @patch("src.services.mssql.mssql_service.pd.read_sql_query")
    def test_auto_connect(self, mock_read_sql, mock_pyodbc_connect):
        """Test auto-connect on query execution"""
        service = MSSQLService("server", "db", "user", "pass")
        assert service.cnxn is None

        service.execute_query("SELECT 1")

        assert service.cnxn is not None
        mock_pyodbc_connect.assert_called_once()

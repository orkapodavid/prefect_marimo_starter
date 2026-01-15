import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add project root to path to allow importing src
sys.path.append(os.getcwd())

from src.shared_utils.prefect_notifications import notify_on_failure, notify_on_success

@pytest.fixture
def mock_flow_context():
    flow = MagicMock()
    flow.name = "Test Flow"
    flow_run = MagicMock()
    flow_run.name = "Test Run"
    state = MagicMock()
    state.name = "Failed"
    state.message = "Something went wrong"
    return flow, flow_run, state

@patch("src.shared_utils.prefect_notifications.get_settings")
@patch("src.shared_utils.prefect_notifications.ExchangeEmailService")
def test_notify_on_failure(mock_service_cls, mock_get_settings, mock_flow_context):
    # Setup mocks
    mock_settings = MagicMock()
    mock_settings.exchange_username = "test@company.com"
    mock_settings.exchange_password = "secret_password"
    mock_settings.exchange_ews_url = "https://mail.company.com/EWS/Exchange.asmx"
    mock_settings.notification_email = "admin@company.com"
    mock_get_settings.return_value = mock_settings

    mock_service = mock_service_cls.return_value

    flow, flow_run, state = mock_flow_context

    # Execute
    notify_on_failure(flow, flow_run, state)

    # Verify
    mock_service_cls.assert_called_with(
        username="test@company.com",
        password="secret_password",
        ews_url="https://mail.company.com/EWS/Exchange.asmx"
    )

    mock_service.send_email.assert_called_once()
    args, kwargs = mock_service.send_email.call_args
    assert kwargs['to_recipients'] == ["admin@company.com"]
    assert "❌ Flow Failed" in kwargs['subject']
    assert "Something went wrong" in kwargs['body']

@patch("src.shared_utils.prefect_notifications.get_settings")
@patch("src.shared_utils.prefect_notifications.ExchangeEmailService")
def test_notify_on_success(mock_service_cls, mock_get_settings, mock_flow_context):
    # Setup mocks
    mock_settings = MagicMock()
    mock_settings.exchange_username = "test@company.com"
    mock_settings.exchange_password = "secret_password"
    mock_settings.exchange_ews_url = None
    mock_settings.notification_email = "admin@company.com"
    mock_get_settings.return_value = mock_settings

    mock_service = mock_service_cls.return_value

    flow, flow_run, state = mock_flow_context
    state.name = "Completed"
    state.message = "All good"

    # Execute
    notify_on_success(flow, flow_run, state)

    # Verify
    mock_service.send_email.assert_called_once()
    args, kwargs = mock_service.send_email.call_args
    assert "✅ Flow Succeeded" in kwargs['subject']

@patch("src.shared_utils.prefect_notifications.get_settings")
@patch("src.shared_utils.prefect_notifications.ExchangeEmailService")
def test_notification_disabled_no_password(mock_service_cls, mock_get_settings, mock_flow_context):
    # Setup mocks: No password
    mock_settings = MagicMock()
    mock_settings.exchange_password = ""
    mock_get_settings.return_value = mock_settings

    flow, flow_run, state = mock_flow_context

    # Execute
    notify_on_failure(flow, flow_run, state)

    # Verify service NOT initialized
    mock_service_cls.assert_not_called()

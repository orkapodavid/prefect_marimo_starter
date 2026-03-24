from unittest.mock import MagicMock, patch

from src.services.x_monitor.x_monitor_gmail_api import (
    GmailApiProvider,
    build_gmail_api_credentials,
)


def test_gmail_api_credentials_explicit_oauth(tmp_path):
    creds_file = tmp_path / "client.json"
    creds_file.write_text('{"installed": {}}', encoding="utf-8")
    token_file = tmp_path / "token.json"

    with patch("src.services.x_monitor.x_monitor_gmail_api.InstalledAppFlow") as mock_flow:
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_flow.from_client_secrets_file.return_value.run_local_server.return_value = (
            mock_creds
        )

        creds = build_gmail_api_credentials(
            credentials_file=str(creds_file),
            token_file=str(token_file),
            use_adc=False,
        )
        assert creds is not None


def test_gmail_api_credentials_adc_path():
    with patch("google.auth.default") as mock_default:
        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, "project-id")

        creds = build_gmail_api_credentials(
            credentials_file="",
            token_file="",
            use_adc=True,
        )
        assert creds is mock_creds
        mock_default.assert_called_once()


def test_gmail_api_provider_sends_email():
    service = MagicMock()
    execute = service.users.return_value.messages.return_value.send.return_value.execute

    provider = GmailApiProvider(service=service, from_addr="test@gmail.com")
    result = provider.send_email(
        to=["alerts@example.com"],
        subject="[X Monitor] test",
        text_body="test body",
        html_body="<p>test body</p>",
    )

    assert result.sent is True
    execute.assert_called_once()

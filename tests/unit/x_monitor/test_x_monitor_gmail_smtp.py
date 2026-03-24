from unittest.mock import MagicMock, patch

from src.services.x_monitor.x_monitor_gmail_smtp import GmailSmtpProvider


def test_gmail_smtp_provider_sends_email():
    provider = GmailSmtpProvider(
        host="smtp.gmail.com",
        port=587,
        username="test@gmail.com",
        password="app_password",
        from_addr="test@gmail.com",
        use_starttls=True,
    )

    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        result = provider.send_email(
            to=["alerts@example.com"],
            subject="[X Monitor] test",
            text_body="test body",
            html_body="<p>test body</p>",
        )

        assert result.sent is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@gmail.com", "app_password")


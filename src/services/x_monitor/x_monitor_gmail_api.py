"""Gmail API provider for X monitor notifications."""

from base64 import urlsafe_b64encode
from email.message import EmailMessage
from pathlib import Path

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from services.x_monitor.x_monitor_notifications import SendResult

GMAIL_SEND_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def build_gmail_api_credentials(
    credentials_file: str,
    token_file: str,
    use_adc: bool,
):
    """Build Gmail API credentials using either ADC or installed-app OAuth."""
    if use_adc:
        credentials, _ = google.auth.default(scopes=GMAIL_SEND_SCOPES)
        return credentials

    if not credentials_file:
        raise ValueError("credentials_file is required when use_adc is False")

    token_path = Path(token_file) if token_file else None
    credentials = None
    if token_path and token_path.exists():
        credentials = Credentials.from_authorized_user_file(
            str(token_path),
            scopes=GMAIL_SEND_SCOPES,
        )

    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_file,
            scopes=GMAIL_SEND_SCOPES,
        )
        credentials = flow.run_local_server(port=0)

    if token_path:
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_payload = credentials.to_json()
        token_path.write_text(
            token_payload if isinstance(token_payload, str) else str(token_payload),
            encoding="utf-8",
        )
    return credentials


class GmailApiProvider:
    """Send email through the Gmail API."""

    def __init__(self, *, service=None, credentials=None, from_addr: str = "") -> None:
        if service is None:
            if credentials is None:
                raise ValueError("credentials are required when service is not provided")
            service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        self.service = service
        self.from_addr = from_addr

    def send_email(
        self,
        *,
        to: list[str],
        subject: str,
        text_body: str,
        html_body: str | None,
        reply_to: str | None = None,
    ) -> SendResult:
        message = EmailMessage()
        if self.from_addr:
            message["From"] = self.from_addr
        message["To"] = ", ".join(to)
        message["Subject"] = subject
        if reply_to:
            message["Reply-To"] = reply_to
        message.set_content(text_body)
        if html_body:
            message.add_alternative(html_body, subtype="html")

        encoded_message = urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        try:
            (
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": encoded_message})
                .execute()
            )
        except Exception as exc:  # pragma: no cover - exercised via return contract
            return SendResult(sent=False, error=str(exc))

        return SendResult(sent=True)

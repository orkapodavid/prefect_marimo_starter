"""Gmail SMTP provider for X monitor notifications."""

from email.message import EmailMessage
import smtplib

from services.x_monitor.x_monitor_notifications import SendResult


class GmailSmtpProvider:
    """Send email through Gmail SMTP."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        from_addr: str,
        use_starttls: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.use_starttls = use_starttls

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
        message["From"] = self.from_addr
        message["To"] = ", ".join(to)
        message["Subject"] = subject
        if reply_to:
            message["Reply-To"] = reply_to
        message.set_content(text_body)
        if html_body:
            message.add_alternative(html_body, subtype="html")

        try:
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_starttls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(message)
        except Exception as exc:  # pragma: no cover - exercised via return contract
            return SendResult(sent=False, error=str(exc))

        return SendResult(sent=True)


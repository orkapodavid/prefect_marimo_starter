import logging
import os
from typing import Optional

from prefect.blocks.system import Secret
from src.services.exchange_email.exchange_email_service import ExchangeEmailService
from src.shared_utils.config import get_settings

logger = logging.getLogger(__name__)

def _get_exchange_service() -> Optional[ExchangeEmailService]:
    """
    Helper to get authenticated Exchange service.
    """
    try:
        # Load password from Secret
        try:
            password_block = Secret.load("exchange-password")
            password = password_block.get()
        except ValueError:
            logger.warning("Secret 'exchange-password' not found. Notifications disabled.")
            return None

        # Determine sender username
        # Try environment variable or fallback
        username = os.environ.get("EXCHANGE_USERNAME", "user@company.com")

        # Determine EWS URL (optional)
        ews_url = os.environ.get("EXCHANGE_EWS_URL")

        return ExchangeEmailService(username=username, password=password, ews_url=ews_url)
    except Exception as e:
        logger.error(f"Failed to initialize Exchange service: {e}")
        return None

def _send_notification(flow, flow_run, state, subject_prefix: str):
    """
    Internal helper to send notification.
    """
    service = _get_exchange_service()
    if not service:
        return

    settings = get_settings()
    recipient = settings.notification_email if settings.notification_email else "admin@company.com"

    subject = f"{subject_prefix}: {flow.name}"
    body = f"""
    Flow run {flow_run.name} entered state {state.name}.

    Message: {state.message}
    """

    try:
        service.send_email(
            to_recipients=[recipient],
            subject=subject,
            body=body
        )
        logger.info(f"Notification sent to {recipient}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

def notify_on_failure(flow, flow_run, state):
    """
    Prefect hook to notify on flow failure.
    """
    _send_notification(flow, flow_run, state, "❌ Flow Failed")

def notify_on_success(flow, flow_run, state):
    """
    Prefect hook to notify on flow success.
    """
    _send_notification(flow, flow_run, state, "✅ Flow Succeeded")

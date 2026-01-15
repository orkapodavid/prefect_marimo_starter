import logging
import os
from typing import Optional

from src.services.exchange_email.exchange_email_service import ExchangeEmailService
from src.shared_utils.config import get_settings

logger = logging.getLogger(__name__)

def _get_exchange_service() -> Optional[ExchangeEmailService]:
    """
    Helper to get authenticated Exchange service.
    """
    try:
        settings = get_settings()

        username = settings.exchange_username
        password = settings.exchange_password
        ews_url = settings.exchange_ews_url

        if not password:
            logger.warning("Exchange password not configured in settings. Notifications disabled.")
            return None

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
    recipient = settings.notification_email

    if not recipient:
        logger.warning("Notification email not configured. Skipping notification.")
        return

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

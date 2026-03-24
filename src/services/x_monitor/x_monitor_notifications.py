"""Notification helpers and provider contracts for X monitor."""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.engine import Engine

from services.x_monitor.x_monitor_tables import tbl_x_monitor_notification_events


class SendResult(Protocol):
    """Structural type shared by notification providers."""

    sent: bool
    error: str | None


class EmailProvider(Protocol):
    """Email sending interface shared by Gmail providers."""

    def send_email(
        self,
        *,
        to: list[str],
        subject: str,
        text_body: str,
        html_body: str | None,
        reply_to: str | None = None,
    ) -> SendResult: ...


def generate_idempotency_key(
    kind: str,
    recipient: str,
    post_id: str | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
) -> str:
    """Create the idempotency key for a notification event."""
    if kind == "immediate_alert":
        if not post_id:
            raise ValueError("post_id is required for immediate alerts")
        return f"immediate:{recipient}:{post_id}"

    if kind == "digest":
        if not window_start or not window_end:
            raise ValueError("window_start and window_end are required for digests")
        return f"digest:{recipient}:{window_start}:{window_end}"

    raise ValueError(f"Unsupported notification kind: {kind}")


def insert_notification_event(engine: Engine, event: dict) -> bool:
    """Insert a notification event if its idempotency key has not been seen."""
    with engine.begin() as connection:
        existing_row = connection.execute(
            select(tbl_x_monitor_notification_events.c.id).where(
                tbl_x_monitor_notification_events.c.idempotency_key
                == event["idempotency_key"]
            )
        ).first()
        if existing_row is not None:
            return False

        payload = {
            "post_id": event.get("post_id"),
            "target_id": event.get("target_id"),
            "kind": event["kind"],
            "provider": event["provider"],
            "recipient": event["recipient"],
            "subject": event["subject"],
            "status": event.get("status", "pending"),
            "attempt_count": event.get("attempt_count", 0),
            "last_attempt_at": event.get("last_attempt_at"),
            "sent_at": event.get("sent_at"),
            "error_message": event.get("error_message"),
            "payload_json": event.get("payload_json", {}),
            "idempotency_key": event["idempotency_key"],
            "created_at": event.get("created_at", datetime.now(UTC)),
        }
        connection.execute(
            tbl_x_monitor_notification_events.insert().values(
                id=event["id"],
                **payload,
            )
        )
        return True


def mark_notification_sent(engine: Engine, notification_id: str, sent_at: datetime) -> None:
    """Mark a notification event as sent."""
    with engine.begin() as connection:
        connection.execute(
            update(tbl_x_monitor_notification_events)
            .where(tbl_x_monitor_notification_events.c.id == notification_id)
            .values(
                status="sent",
                sent_at=sent_at,
                last_attempt_at=sent_at,
                attempt_count=tbl_x_monitor_notification_events.c.attempt_count + 1,
                error_message=None,
            )
        )


def mark_notification_failed(
    engine: Engine,
    notification_id: str,
    error_message: str,
) -> None:
    """Mark a notification event as failed."""
    failed_at = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            update(tbl_x_monitor_notification_events)
            .where(tbl_x_monitor_notification_events.c.id == notification_id)
            .values(
                status="failed",
                last_attempt_at=failed_at,
                attempt_count=tbl_x_monitor_notification_events.c.attempt_count + 1,
                error_message=error_message,
            )
        )

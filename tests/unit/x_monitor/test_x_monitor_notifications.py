from datetime import UTC, datetime

from sqlalchemy import select

from services.x_monitor.x_monitor_notifications import (
    generate_idempotency_key,
    insert_notification_event,
    mark_notification_failed,
    mark_notification_sent,
)
from services.x_monitor.x_monitor_tables import tbl_x_monitor_notification_events


def test_immediate_alert_idempotency_key():
    key = generate_idempotency_key(
        kind="immediate_alert",
        recipient="alerts@example.com",
        post_id="1234567890",
    )
    assert key == "immediate:alerts@example.com:1234567890"


def test_digest_idempotency_key():
    key = generate_idempotency_key(
        kind="digest",
        recipient="digest@example.com",
        window_start="2026-03-24T00:00:00",
        window_end="2026-03-24T23:59:59",
    )
    assert key == "digest:digest@example.com:2026-03-24T00:00:00:2026-03-24T23:59:59"


def test_insert_notification_event_is_idempotent(in_memory_x_monitor_engine):
    event = {
        "id": "notif-1",
        "kind": "immediate_alert",
        "provider": "gmail_smtp",
        "recipient": "alerts@example.com",
        "subject": "subject",
        "status": "pending",
        "attempt_count": 0,
        "payload_json": {},
        "idempotency_key": "immediate:alerts@example.com:123",
        "created_at": datetime.now(UTC),
    }

    inserted_first = insert_notification_event(in_memory_x_monitor_engine, event)
    inserted_second = insert_notification_event(in_memory_x_monitor_engine, event)

    assert inserted_first is True
    assert inserted_second is False


def test_mark_notification_sent_and_failed(in_memory_x_monitor_engine):
    created_at = datetime.now(UTC)
    insert_notification_event(
        in_memory_x_monitor_engine,
        {
            "id": "notif-2",
            "kind": "immediate_alert",
            "provider": "gmail_smtp",
            "recipient": "alerts@example.com",
            "subject": "subject",
            "status": "pending",
            "attempt_count": 0,
            "payload_json": {},
            "idempotency_key": "immediate:alerts@example.com:456",
            "created_at": created_at,
        },
    )

    sent_at = datetime.now(UTC)
    mark_notification_sent(in_memory_x_monitor_engine, "notif-2", sent_at)

    with in_memory_x_monitor_engine.begin() as connection:
        sent_row = connection.execute(
            select(tbl_x_monitor_notification_events).where(
                tbl_x_monitor_notification_events.c.id == "notif-2"
            )
        ).mappings().one()
    assert sent_row["status"] == "sent"
    assert sent_row["sent_at"] == sent_at.replace(tzinfo=None)

    mark_notification_failed(
        in_memory_x_monitor_engine,
        "notif-2",
        "smtp error",
    )

    with in_memory_x_monitor_engine.begin() as connection:
        failed_row = connection.execute(
            select(tbl_x_monitor_notification_events).where(
                tbl_x_monitor_notification_events.c.id == "notif-2"
            )
        ).mappings().one()
    assert failed_row["status"] == "failed"
    assert failed_row["error_message"] == "smtp error"

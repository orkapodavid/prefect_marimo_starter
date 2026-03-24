"""Digest grouping and delivery helpers for X monitor."""

from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.engine import Engine

from services.x_monitor.x_monitor_notifications import (
    generate_idempotency_key,
    insert_notification_event,
    mark_notification_failed,
    mark_notification_sent,
)
from services.x_monitor.x_monitor_tables import X_MONITOR_METADATA

tbl_x_monitor_targets = X_MONITOR_METADATA.tables["tblXMonitorTargets"]
tbl_x_monitor_posts = X_MONITOR_METADATA.tables["tblXMonitorPosts"]
tbl_x_monitor_post_matches = X_MONITOR_METADATA.tables["tblXMonitorPostMatches"]
tbl_x_monitor_digest_bookmarks = X_MONITOR_METADATA.tables["tblXMonitorDigestBookmarks"]

_TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
    autoescape=select_autoescape(["html"]),
)


def _get_setting(settings, name: str, default):
    if isinstance(settings, dict):
        return settings.get(name, default)
    return getattr(settings, name, default)


def _created_at_sort_key(item: dict):
    value = item["created_at"]
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def group_digest_items(items: list[dict]) -> dict[str, dict[str, list[dict]]]:
    """Group digest items by recipient and then by username, newest first."""
    grouped: dict[str, dict[str, list[dict]]] = {}
    for item in items:
        recipient_group = grouped.setdefault(item["recipient"], {})
        account_items = recipient_group.setdefault(item["username"], [])
        account_items.append(item)

    for recipient_accounts in grouped.values():
        for account_items in recipient_accounts.values():
            account_items.sort(key=_created_at_sort_key, reverse=True)
    return grouped


def compute_digest_window(timezone: str) -> tuple[datetime, datetime]:
    """Return the previous full local-day digest window."""
    zone = ZoneInfo(timezone)
    local_now = datetime.now(zone)
    window_end = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_start = window_end - timedelta(days=1)
    return window_start, window_end


def collect_digest_items(
    engine: Engine,
    window_start: datetime,
    window_end: datetime,
) -> list[dict]:
    """Collect matched posts that have not yet been sent in the recipient's digest window."""
    with engine.begin() as connection:
        matched_rows = connection.execute(
            select(
                tbl_x_monitor_posts.c.post_id,
                tbl_x_monitor_posts.c.author_username,
                tbl_x_monitor_posts.c.created_at,
                tbl_x_monitor_posts.c.text_raw,
                tbl_x_monitor_posts.c.url,
                tbl_x_monitor_post_matches.c.matched_rules,
                tbl_x_monitor_targets.c.digest_recipients,
            )
            .join(
                tbl_x_monitor_post_matches,
                tbl_x_monitor_post_matches.c.post_id == tbl_x_monitor_posts.c.id,
            )
            .join(
                tbl_x_monitor_targets,
                tbl_x_monitor_targets.c.id == tbl_x_monitor_posts.c.target_id,
            )
            .where(tbl_x_monitor_post_matches.c.matched.is_(True))
            .where(tbl_x_monitor_posts.c.created_at >= window_start)
            .where(tbl_x_monitor_posts.c.created_at < window_end)
        ).mappings().all()
        bookmark_rows = {
            row["digest_key"]
            for row in connection.execute(select(tbl_x_monitor_digest_bookmarks.c.digest_key)).mappings()
        }

    items: list[dict] = []
    for row in matched_rows:
        for recipient in row["digest_recipients"] or []:
            digest_key = generate_idempotency_key(
                kind="digest",
                recipient=recipient,
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
            )
            if digest_key in bookmark_rows:
                continue
            items.append(
                {
                    "recipient": recipient,
                    "username": row["author_username"],
                    "post_id": row["post_id"],
                    "created_at": row["created_at"],
                    "text_raw": row["text_raw"],
                    "url": row["url"],
                    "matched_rules": row["matched_rules"],
                }
            )
    return items


def send_digest_for_recipient(
    engine: Engine,
    email_provider,
    recipient: str,
    items: list[dict],
    window: tuple[datetime, datetime],
    settings,
) -> dict:
    """Render and send a digest email for one recipient."""
    window_start, window_end = window
    if not items:
        return {"recipient": recipient, "sent": False, "status": "skipped"}

    idempotency_key = generate_idempotency_key(
        kind="digest",
        recipient=recipient,
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
    )
    notification_id = str(uuid4())
    subject_prefix = _get_setting(settings, "x_monitor_subject_prefix", "[X Monitor]")
    subject = f"{subject_prefix} Daily digest"
    posts_by_account = group_digest_items(
        [{**item, "recipient": recipient} for item in items]
    )[recipient]
    context = {
        "subject_prefix": subject_prefix,
        "window_start": window_start,
        "window_end": window_end,
        "posts_by_account": posts_by_account,
    }
    text_body = _TEMPLATE_ENV.get_template("digest.txt.j2").render(**context)
    html_body = _TEMPLATE_ENV.get_template("digest.html.j2").render(**context)

    inserted = insert_notification_event(
        engine,
        {
            "id": notification_id,
            "kind": "digest",
            "provider": _get_setting(settings, "x_monitor_gmail_provider", "gmail_smtp"),
            "recipient": recipient,
            "subject": subject,
            "status": "pending",
            "payload_json": {"text_body": text_body, "html_body": html_body},
            "idempotency_key": idempotency_key,
            "created_at": datetime.now(window_start.tzinfo),
        },
    )
    if not inserted:
        return {"recipient": recipient, "sent": False, "status": "duplicate"}

    result = email_provider.send_email(
        to=[recipient],
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
    if result.sent:
        sent_at = datetime.now(window_start.tzinfo)
        mark_notification_sent(engine, notification_id, sent_at)
        with engine.begin() as connection:
            connection.execute(
                tbl_x_monitor_digest_bookmarks.insert().values(
                    digest_key=idempotency_key,
                    window_start=window_start,
                    window_end=window_end,
                    sent_at=sent_at,
                    recipient=recipient,
                )
            )
        return {"recipient": recipient, "sent": True, "status": "sent", "items": len(items)}

    mark_notification_failed(engine, notification_id, result.error or "unknown send error")
    return {"recipient": recipient, "sent": False, "status": "failed", "items": len(items)}

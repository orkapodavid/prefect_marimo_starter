"""Core polling orchestration for X monitor."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select, update
from sqlalchemy.engine import Engine

from services.x_monitor.x_monitor_matching import evaluate_target_match
from services.x_monitor.x_monitor_notifications import (
    generate_idempotency_key,
    insert_notification_event,
    mark_notification_failed,
    mark_notification_sent,
)
from services.x_monitor.x_monitor_tables import X_MONITOR_METADATA, tbl_x_monitor_targets
from services.x_monitor.x_monitor_targets_sync import ensure_watermark_row
from services.x_monitor.x_monitor_text_normalizer import normalize_post_text

tbl_x_monitor_target_watermarks = X_MONITOR_METADATA.tables["tblXMonitorTargetWatermarks"]
tbl_x_monitor_posts = X_MONITOR_METADATA.tables["tblXMonitorPosts"]
tbl_x_monitor_post_matches = X_MONITOR_METADATA.tables["tblXMonitorPostMatches"]

_TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
    autoescape=select_autoescape(["html"]),
)


def _get_setting(settings, name: str, default):
    if isinstance(settings, dict):
        return settings.get(name, default)
    return getattr(settings, name, default)


def filter_unseen_posts(posts: list[dict], last_seen_post_id: str | None) -> list[dict]:
    """Stop scanning once the previous watermark is reached."""
    if last_seen_post_id is None:
        return posts

    unseen_posts: list[dict] = []
    for post in posts:
        if post["post_id"] == last_seen_post_id:
            break
        unseen_posts.append(post)
    return unseen_posts


def build_poll_run_summary(results: list[dict]) -> dict:
    """Aggregate target-level poll results into a flow summary."""
    return {
        "active_targets": len(results),
        "targets_succeeded": sum(1 for result in results if result.get("status") == "success"),
        "targets_failed": sum(1 for result in results if result.get("status") == "failed"),
        "posts_fetched": sum(result.get("posts_fetched", 0) for result in results),
        "new_posts": sum(result.get("new_posts", 0) for result in results),
        "matches_found": sum(result.get("matches", 0) for result in results),
        "emails_sent": sum(result.get("emails_sent", 0) for result in results),
        "emails_failed": sum(result.get("emails_failed", 0) for result in results),
        "duration_seconds": sum(result.get("duration_seconds", 0) for result in results),
    }


def _render_immediate_alert(target: dict, post: dict, matched_rules: list[str], subject_prefix: str) -> tuple[str, str, str]:
    subject = f"{subject_prefix} @{target['username']} matched: {', '.join(matched_rules) or 'match'}"
    context = {
        "subject_prefix": subject_prefix,
        "username": target["username"],
        "post": post,
        "matched_rules": matched_rules,
    }
    text_body = _TEMPLATE_ENV.get_template("immediate_alert.txt.j2").render(**context)
    html_body = _TEMPLATE_ENV.get_template("immediate_alert.html.j2").render(**context)
    return subject, text_body, html_body


def poll_single_target(engine: Engine, client, email_provider, target: dict, settings) -> dict:
    """Poll one target, persist new state, and send immediate alerts."""
    started_at = datetime.now(UTC)
    ensure_watermark_row(engine, target["id"])

    with engine.begin() as connection:
        watermark_row = connection.execute(
            select(tbl_x_monitor_target_watermarks).where(
                tbl_x_monitor_target_watermarks.c.target_id == target["id"]
            )
        ).mappings().one()

    resolved_user_id = target.get("user_id")
    if not resolved_user_id:
        resolved_user_id = asyncio.run(client.resolve_user_id(target["username"]))
        with engine.begin() as connection:
            connection.execute(
                update(tbl_x_monitor_targets)
                .where(tbl_x_monitor_targets.c.id == target["id"])
                .values(user_id=resolved_user_id, updated_at=datetime.now(UTC))
            )

    fetched_posts = asyncio.run(
        client.fetch_recent_posts(
            user_id=resolved_user_id,
            include_replies=target.get("include_replies", False),
            limit=_get_setting(settings, "x_monitor_poll_batch_limit", 25),
        )
    )
    unseen_posts = filter_unseen_posts(
        fetched_posts,
        watermark_row["last_seen_post_id"],
    )

    inserted_posts: list[dict] = []
    matched_posts: list[dict] = []
    notification_events: list[dict] = []
    now = datetime.now(UTC)

    with engine.begin() as connection:
        existing_post_ids = {
            row["post_id"]
            for row in connection.execute(
                select(tbl_x_monitor_posts.c.post_id).where(
                    tbl_x_monitor_posts.c.post_id.in_([post["post_id"] for post in unseen_posts])
                )
            ).mappings()
        } if unseen_posts else set()

        for post in reversed(unseen_posts):
            if post["post_id"] in existing_post_ids:
                continue

            inserted_post_id = str(uuid4())
            normalized_text = normalize_post_text(post.get("text_raw", ""))
            connection.execute(
                tbl_x_monitor_posts.insert().values(
                    id=inserted_post_id,
                    post_id=post["post_id"],
                    target_id=target["id"],
                    author_username=post.get("author_username", target["username"]),
                    author_user_id=post.get("author_user_id"),
                    created_at=post["created_at"],
                    text_raw=post.get("text_raw", ""),
                    text_normalized=normalized_text,
                    url=post.get("url", ""),
                    is_reply=post.get("is_reply", False),
                    is_retweet=post.get("is_retweet", False),
                    has_media=post.get("has_media", False),
                    lang=post.get("lang"),
                    raw_json=post.get("raw_json", {}),
                    inserted_at=now,
                )
            )
            inserted_posts.append({**post, "db_post_id": inserted_post_id, "text_normalized": normalized_text})

            match_result = evaluate_target_match(target=target, post=post)
            connection.execute(
                tbl_x_monitor_post_matches.insert().values(
                    id=str(uuid4()),
                    post_id=inserted_post_id,
                    target_id=target["id"],
                    matched=match_result.matched,
                    matched_rules=match_result.matched_rules,
                    match_reason=match_result.match_reason,
                    created_at=now,
                )
            )

            if (
                match_result.matched
                and _get_setting(settings, "x_monitor_immediate_alerts_enabled", True)
            ):
                matched_posts.append({**post, "matched_rules": match_result.matched_rules})
                for recipient in target.get("alert_recipients", []):
                    subject, text_body, html_body = _render_immediate_alert(
                        target,
                        post,
                        match_result.matched_rules,
                        _get_setting(settings, "x_monitor_subject_prefix", "[X Monitor]"),
                    )
                    notification_id = str(uuid4())
                    event = {
                        "id": notification_id,
                        "post_id": inserted_post_id,
                        "target_id": target["id"],
                        "kind": "immediate_alert",
                        "provider": target.get(
                            "gmail_provider",
                            _get_setting(settings, "x_monitor_gmail_provider", "gmail_smtp"),
                        ),
                        "recipient": recipient,
                        "subject": subject,
                        "status": "pending",
                        "payload_json": {
                            "text_body": text_body,
                            "html_body": html_body,
                            "matched_rules": match_result.matched_rules,
                        },
                        "idempotency_key": generate_idempotency_key(
                            kind="immediate_alert",
                            recipient=recipient,
                            post_id=post["post_id"],
                        ),
                        "created_at": now,
                    }
                    if insert_notification_event(engine, event):
                        notification_events.append(
                            {
                                "id": notification_id,
                                "recipient": recipient,
                                "subject": subject,
                                "text_body": text_body,
                                "html_body": html_body,
                            }
                        )

    emails_sent = 0
    emails_failed = 0
    for event in notification_events:
        result = email_provider.send_email(
            to=[event["recipient"]],
            subject=event["subject"],
            text_body=event["text_body"],
            html_body=event["html_body"],
        )
        if result.sent:
            emails_sent += 1
            mark_notification_sent(engine, event["id"], datetime.now(UTC))
        else:
            emails_failed += 1
            mark_notification_failed(engine, event["id"], result.error or "unknown send error")

    newest_post = unseen_posts[0] if unseen_posts else None
    with engine.begin() as connection:
        connection.execute(
            update(tbl_x_monitor_target_watermarks)
            .where(tbl_x_monitor_target_watermarks.c.target_id == target["id"])
            .values(
                last_seen_post_id=None if newest_post is None else newest_post["post_id"],
                last_seen_post_time=None if newest_post is None else newest_post["created_at"],
                last_attempted_poll_at=datetime.now(UTC),
                last_successful_poll_at=datetime.now(UTC),
                consecutive_failures=0,
                last_error=None,
            )
        )

    return {
        "target_id": target["id"],
        "status": "success",
        "posts_fetched": len(fetched_posts),
        "new_posts": len(inserted_posts),
        "matches": len(matched_posts),
        "emails_sent": emails_sent,
        "emails_failed": emails_failed,
        "duration_seconds": int((datetime.now(UTC) - started_at).total_seconds()),
    }


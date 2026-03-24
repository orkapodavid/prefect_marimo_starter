"""Bootstrap and backfill helpers for X monitor targets."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.engine import Engine

from services.x_monitor.x_monitor_targets_sync import ensure_watermark_row
from services.x_monitor.x_monitor_tables import X_MONITOR_METADATA, tbl_x_monitor_targets

tbl_x_monitor_target_watermarks = X_MONITOR_METADATA.tables["tblXMonitorTargetWatermarks"]


def bootstrap_target(engine: Engine, client, target: dict, limit: int = 25) -> dict:
    """Resolve a target's user id and seed its watermark from the newest post."""
    resolved_user_id = target.get("user_id") or asyncio.run(
        client.resolve_user_id(target["username"])
    )
    posts = asyncio.run(
        client.fetch_recent_posts(
            user_id=resolved_user_id,
            include_replies=target.get("include_replies", False),
            limit=limit,
        )
    )
    newest_post = max(posts, key=lambda post: post["created_at"], default=None)
    now = datetime.now(UTC)

    ensure_watermark_row(engine, target["id"])

    with engine.begin() as connection:
        connection.execute(
            update(tbl_x_monitor_targets)
            .where(tbl_x_monitor_targets.c.id == target["id"])
            .values(user_id=resolved_user_id, updated_at=now)
        )
        watermark_values = {
            "last_successful_poll_at": now,
            "last_attempted_poll_at": now,
            "consecutive_failures": 0,
            "last_error": None,
        }
        if newest_post is not None:
            watermark_values["last_seen_post_id"] = newest_post["post_id"]
            watermark_values["last_seen_post_time"] = newest_post["created_at"]
        connection.execute(
            update(tbl_x_monitor_target_watermarks)
            .where(tbl_x_monitor_target_watermarks.c.target_id == target["id"])
            .values(**watermark_values)
        )

    return {
        "target_id": target["id"],
        "username": target["username"],
        "user_id": resolved_user_id,
        "last_seen_post_id": None if newest_post is None else newest_post["post_id"],
        "historical_posts_skipped": len(posts),
    }


def backfill_target(engine: Engine, client, target: dict, limit: int = 100) -> dict:
    """Fetch an explicit historical batch for a target without changing flow semantics."""
    resolved_user_id = target.get("user_id") or asyncio.run(
        client.resolve_user_id(target["username"])
    )
    posts = asyncio.run(
        client.fetch_recent_posts(
            user_id=resolved_user_id,
            include_replies=target.get("include_replies", False),
            limit=limit,
        )
    )
    return {
        "target_id": target["id"],
        "username": target["username"],
        "user_id": resolved_user_id,
        "posts": posts,
    }

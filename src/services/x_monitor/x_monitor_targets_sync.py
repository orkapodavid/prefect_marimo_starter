"""Helpers for reconciling configured X monitor targets into the database."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.engine import Engine

from services.x_monitor.x_monitor_tables import tbl_x_monitor_targets
from services.x_monitor.x_monitor_tables import (
    X_MONITOR_METADATA,
)


tbl_x_monitor_target_watermarks = X_MONITOR_METADATA.tables["tblXMonitorTargetWatermarks"]


def sync_targets(engine: Engine, targets: list[dict]) -> None:
    """Upsert configured targets and deactivate any missing ones."""
    now = datetime.now(UTC)
    configured_ids = {target["id"] for target in targets}

    with engine.begin() as connection:
        existing_rows = {
            row["id"]: row
            for row in connection.execute(select(tbl_x_monitor_targets)).mappings().all()
        }

        for target in targets:
            row_payload = {
                "id": target["id"],
                "username": target["username"],
                "user_id": target.get("user_id"),
                "include_replies": target.get("include_replies", False),
                "include_retweets": target.get("include_retweets", False),
                "media_only": target.get("media_only", False),
                "keywords_any": target.get("keywords_any", []),
                "keywords_all": target.get("keywords_all", []),
                "regex_any": target.get("regex_any", []),
                "alert_recipients": target.get("alert_recipients", []),
                "digest_recipients": target.get("digest_recipients", []),
                "active": target.get("active", True),
                "updated_at": now,
            }
            if target["id"] in existing_rows:
                connection.execute(
                    update(tbl_x_monitor_targets)
                    .where(tbl_x_monitor_targets.c.id == target["id"])
                    .values(**row_payload)
                )
            else:
                connection.execute(
                    tbl_x_monitor_targets.insert().values(
                        **row_payload,
                        created_at=now,
                    )
                )

            ensure_watermark_row(engine, target["id"])

        if configured_ids:
            connection.execute(
                update(tbl_x_monitor_targets)
                .where(tbl_x_monitor_targets.c.id.not_in(configured_ids))
                .values(active=False, updated_at=now)
            )
        else:
            connection.execute(
                update(tbl_x_monitor_targets).values(active=False, updated_at=now)
            )


def list_targets(engine: Engine, include_inactive: bool = False) -> list[dict]:
    """List persisted targets as plain dictionaries."""
    statement = select(tbl_x_monitor_targets)
    if not include_inactive:
        statement = statement.where(tbl_x_monitor_targets.c.active.is_(True))

    with engine.begin() as connection:
        return list(connection.execute(statement).mappings().all())


def ensure_watermark_row(engine: Engine, target_id: str) -> None:
    """Insert a watermark row if one does not already exist."""
    with engine.begin() as connection:
        existing_row = connection.execute(
            select(tbl_x_monitor_target_watermarks.c.target_id).where(
                tbl_x_monitor_target_watermarks.c.target_id == target_id
            )
        ).first()
        if existing_row is None:
            connection.execute(
                tbl_x_monitor_target_watermarks.insert().values(
                    target_id=target_id,
                    consecutive_failures=0,
                )
            )


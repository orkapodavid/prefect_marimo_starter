from datetime import datetime
from zoneinfo import ZoneInfo

from freezegun import freeze_time

from src.services.x_monitor.x_monitor_digest import (
    compute_digest_window,
    group_digest_items,
)


def test_group_digest_items_by_recipient_then_account():
    items = [
        {
            "recipient": "a@b.com",
            "username": "openai",
            "post_id": "1",
            "created_at": "2026-03-24T02:00:00Z",
        },
        {
            "recipient": "a@b.com",
            "username": "openai",
            "post_id": "2",
            "created_at": "2026-03-24T01:00:00Z",
        },
        {
            "recipient": "a@b.com",
            "username": "nvidia",
            "post_id": "3",
            "created_at": "2026-03-24T03:00:00Z",
        },
        {
            "recipient": "c@d.com",
            "username": "openai",
            "post_id": "4",
            "created_at": "2026-03-24T01:00:00Z",
        },
    ]
    grouped = group_digest_items(items)

    assert "a@b.com" in grouped
    assert "c@d.com" in grouped
    assert "openai" in grouped["a@b.com"]
    assert "nvidia" in grouped["a@b.com"]
    assert grouped["a@b.com"]["openai"][0]["post_id"] == "1"


@freeze_time("2026-03-25 08:00:00")
def test_compute_digest_window_uses_previous_local_day():
    window_start, window_end = compute_digest_window("Asia/Singapore")

    assert window_start == datetime(2026, 3, 24, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    assert window_end == datetime(2026, 3, 25, 0, 0, tzinfo=ZoneInfo("Asia/Singapore"))

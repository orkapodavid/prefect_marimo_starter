from services.x_monitor.x_monitor_targets_sync import list_targets, sync_targets


def test_sync_targets_upserts_by_target_id(in_memory_x_monitor_engine):
    targets = [
        {
            "id": "openai_posts",
            "username": "openai",
            "alert_recipients": ["alerts@example.com"],
            "digest_recipients": ["digest@example.com"],
        }
    ]
    sync_targets(in_memory_x_monitor_engine, targets)

    targets[0]["alert_recipients"] = ["ops@example.com"]
    sync_targets(in_memory_x_monitor_engine, targets)

    rows = list_targets(in_memory_x_monitor_engine)
    assert len(rows) == 1
    assert rows[0]["alert_recipients"] == ["ops@example.com"]


def test_sync_targets_deactivates_removed_targets(in_memory_x_monitor_engine):
    sync_targets(
        in_memory_x_monitor_engine,
        [
            {
                "id": "old_target",
                "username": "old_account",
                "alert_recipients": ["a@b.com"],
                "digest_recipients": ["a@b.com"],
            }
        ],
    )

    sync_targets(in_memory_x_monitor_engine, [])

    rows = list_targets(in_memory_x_monitor_engine, include_inactive=True)
    assert len(rows) == 1
    assert rows[0]["active"] is False


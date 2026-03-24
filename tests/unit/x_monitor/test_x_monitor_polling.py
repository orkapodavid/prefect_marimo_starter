from src.services.x_monitor.x_monitor_polling import (
    build_poll_run_summary,
    filter_unseen_posts,
)


def test_filter_unseen_posts_stops_at_watermark():
    posts = [
        {"post_id": "c", "created_at": "2026-03-24T03:00:00Z"},
        {"post_id": "b", "created_at": "2026-03-24T02:00:00Z"},
        {"post_id": "a", "created_at": "2026-03-24T01:00:00Z"},
    ]
    unseen = filter_unseen_posts(posts, last_seen_post_id="b")
    assert len(unseen) == 1
    assert unseen[0]["post_id"] == "c"


def test_filter_unseen_posts_returns_all_when_no_watermark():
    posts = [
        {"post_id": "c", "created_at": "2026-03-24T03:00:00Z"},
        {"post_id": "b", "created_at": "2026-03-24T02:00:00Z"},
    ]
    unseen = filter_unseen_posts(posts, last_seen_post_id=None)
    assert len(unseen) == 2


def test_build_poll_run_summary_aggregates_counts():
    summary = build_poll_run_summary(
        [
            {
                "status": "success",
                "posts_fetched": 3,
                "new_posts": 2,
                "matches": 1,
                "emails_sent": 1,
                "emails_failed": 0,
            },
            {
                "status": "failed",
                "posts_fetched": 0,
                "new_posts": 0,
                "matches": 0,
                "emails_sent": 0,
                "emails_failed": 1,
            },
        ]
    )

    assert summary["active_targets"] == 2
    assert summary["targets_succeeded"] == 1
    assert summary["targets_failed"] == 1
    assert summary["posts_fetched"] == 3
    assert summary["new_posts"] == 2
    assert summary["matches_found"] == 1
    assert summary["emails_sent"] == 1
    assert summary["emails_failed"] == 1


from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from services.x_monitor.x_monitor_bootstrap import bootstrap_target
from services.x_monitor.x_monitor_tables import X_MONITOR_METADATA
from services.x_monitor.x_monitor_targets_sync import sync_targets
from src.services.x_monitor.x_monitor_twscrape_client import XMonitorTwscrapeClient


@pytest.fixture
def mock_twscrape_api():
    api = MagicMock()
    api.user_tweets = AsyncMock(return_value=[])
    api.user_tweets_and_replies = AsyncMock(return_value=[])
    api.user_by_login = AsyncMock(return_value=MagicMock(id=12345, username="openai"))
    return api


@pytest.mark.asyncio
async def test_client_uses_replies_endpoint_when_enabled(mock_twscrape_api):
    client = XMonitorTwscrapeClient(api=mock_twscrape_api)
    await client.fetch_recent_posts(user_id="123", include_replies=True, limit=25)
    mock_twscrape_api.user_tweets_and_replies.assert_called_once_with("123", limit=25)


@pytest.mark.asyncio
async def test_client_uses_posts_endpoint_when_replies_disabled(mock_twscrape_api):
    client = XMonitorTwscrapeClient(api=mock_twscrape_api)
    await client.fetch_recent_posts(user_id="123", include_replies=False, limit=25)
    mock_twscrape_api.user_tweets.assert_called_once_with("123", limit=25)


@pytest.mark.asyncio
async def test_client_resolves_user_id(mock_twscrape_api):
    client = XMonitorTwscrapeClient(api=mock_twscrape_api)
    user_id = await client.resolve_user_id("openai")
    assert user_id == "12345"


def test_bootstrap_target_sets_latest_watermark_without_notifications(
    in_memory_x_monitor_engine,
):
    sync_targets(
        in_memory_x_monitor_engine,
        [
            {
                "id": "openai_posts",
                "username": "openai",
                "alert_recipients": ["alerts@example.com"],
                "digest_recipients": ["digest@example.com"],
            }
        ],
    )

    client = MagicMock()
    client.resolve_user_id = AsyncMock(return_value="12345")
    client.fetch_recent_posts = AsyncMock(
        return_value=[
            {
                "post_id": "post-2",
                "created_at": datetime(2026, 3, 24, 12, 0, tzinfo=UTC),
            },
            {
                "post_id": "post-1",
                "created_at": datetime(2026, 3, 24, 11, 0, tzinfo=UTC),
            },
        ]
    )

    result = bootstrap_target(
        in_memory_x_monitor_engine,
        client,
        {
            "id": "openai_posts",
            "username": "openai",
            "include_replies": False,
        },
    )

    target_table = X_MONITOR_METADATA.tables["tblXMonitorTargets"]
    watermark_table = X_MONITOR_METADATA.tables["tblXMonitorTargetWatermarks"]

    with in_memory_x_monitor_engine.begin() as connection:
        target_row = connection.execute(
            select(target_table).where(target_table.c.id == "openai_posts")
        ).mappings().one()
        watermark_row = connection.execute(
            select(watermark_table).where(watermark_table.c.target_id == "openai_posts")
        ).mappings().one()

    assert result["user_id"] == "12345"
    assert result["last_seen_post_id"] == "post-2"
    assert target_row["user_id"] == "12345"
    assert watermark_row["last_seen_post_id"] == "post-2"

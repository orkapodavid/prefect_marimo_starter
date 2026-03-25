from datetime import date
import json
from pathlib import Path

import pytest

from services.tdnet.tdnet_announcement_models import (
    TdnetAnnouncement,
    TdnetLanguage,
    TdnetScrapeResult,
)


@pytest.fixture
def financial_monitor_fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "fixtures" / "financial_monitor"


@pytest.fixture
def tdnet_scrape_result(financial_monitor_fixtures_dir: Path) -> TdnetScrapeResult:
    payload = json.loads(
        (financial_monitor_fixtures_dir / "tdnet/tdnet_announcements.json").read_text(
            encoding="utf-8"
        )
    )
    announcements = [TdnetAnnouncement.model_validate(item) for item in payload["announcements"]]
    return TdnetScrapeResult(
        start_date=date.fromisoformat(payload["start_date"]),
        end_date=date.fromisoformat(payload["end_date"]),
        total_count=payload["total_count"],
        page_count=payload["page_count"],
        announcements=announcements,
        language=TdnetLanguage(payload["language"]),
    )


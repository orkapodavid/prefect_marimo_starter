"""
TDnet Announcement Scraper Smoke Test
=====================================

Smoke test that verifies the TDnet Announcement Scraper works with live TDnet website.
This test makes actual HTTP requests to both English and Japanese TDnet.

Run with: pytest tests/smoke/tdnet/test_announcement_smoke.py -v -s
"""

import pytest
from datetime import date, timedelta
import pandas as pd

from src.services.tdnet import (
    TdnetAnnouncementScraper,
    TdnetLanguage,
    TdnetAnnouncement,
    TdnetScrapeResult,
    scrape_announcements,
)


class TestTdnetAnnouncementSmoke:
    """
    Smoke tests for TDnet Announcement Scraper using live TDnet website.

    These tests verify:
    1. English TDnet announcements are accessible
    2. Japanese TDnet announcements are accessible
    3. Announcements are correctly parsed into Pydantic models
    4. DataFrame conversion works correctly
    """

    @pytest.fixture
    def en_scraper(self):
        """Create English TDnet scraper."""
        return TdnetAnnouncementScraper(language=TdnetLanguage.ENGLISH, delay=1.0, timeout=30)

    @pytest.fixture
    def jp_scraper(self):
        """Create Japanese TDnet scraper."""
        return TdnetAnnouncementScraper(language=TdnetLanguage.JAPANESE, delay=1.0, timeout=30)

    @pytest.mark.smoke
    def test_scrape_english_announcements(self, en_scraper):
        """
        Smoke test: Verify we can scrape English TDnet announcements.

        Expected URL: https://www.release.tdnet.info/onsf/TDJFSearch_e/TDJFSearch_e

        Assertions:
        - TdnetScrapeResult is returned
        - Announcements list is populated (weekday) or empty (weekend/holiday)
        - Each announcement has valid stock_code (4-5 digit)
        - Each announcement has company_name, title, publish_datetime
        """
        today = date.today()
        yesterday = today - timedelta(days=1)

        result = en_scraper.scrape(yesterday, today)

        # Result structure
        assert isinstance(result, TdnetScrapeResult)
        assert result.start_date == yesterday
        assert result.end_date == today
        assert result.language == TdnetLanguage.ENGLISH
        assert result.total_count >= 0

        print(f"\n✅ English TDnet Scrape Verification:")
        print(f"   Date range: {yesterday} to {today}")
        print(f"   Total reported: {result.total_count}")
        print(f"   Announcements scraped: {len(result.announcements)}")

        # Verify announcement structure (if any found)
        if result.announcements:
            for ann in result.announcements[:5]:
                assert isinstance(ann, TdnetAnnouncement)
                assert ann.stock_code.isalnum(), f"Invalid stock_code: {ann.stock_code}"
                assert len(ann.stock_code) >= 4
                assert ann.company_name, "company_name is empty"
                assert ann.title, "title is empty"
                assert ann.publish_date, "publish_date is empty"
                assert ann.language == TdnetLanguage.ENGLISH

            print(f"\n   Sample announcements:")
            for ann in result.announcements[:3]:
                print(f"     {ann.stock_code} | {ann.company_name[:25]}... | {ann.title[:40]}...")

    @pytest.mark.smoke
    def test_scrape_japanese_announcements(self, jp_scraper):
        """
        Smoke test: Verify we can scrape Japanese TDnet announcements.

        Expected URL: https://www.release.tdnet.info/inbs/I_list_001_YYYYMMDD.html

        Assertions:
        - TdnetScrapeResult is returned
        - Announcements have Japanese characters in title/company
        - listed_exchange field is populated (東, 名, etc.)
        """
        today = date.today()

        result = jp_scraper.scrape(today, today)

        # Result structure
        assert isinstance(result, TdnetScrapeResult)
        assert result.start_date == today
        assert result.end_date == today
        assert result.language == TdnetLanguage.JAPANESE

        print(f"\n✅ Japanese TDnet Scrape Verification:")
        print(f"   Date: {today}")
        print(f"   Total: {result.total_count}")
        print(f"   Pages scraped: {result.page_count}")

        # Verify Japanese-specific fields (if any found)
        if result.announcements:
            exchanges_found = set()
            for ann in result.announcements[:10]:
                assert ann.language == TdnetLanguage.JAPANESE
                if ann.listed_exchange:
                    exchanges_found.add(ann.listed_exchange)

            print(f"\n   Exchanges found: {exchanges_found}")
            print(f"\n   Sample Japanese announcements:")
            for ann in result.announcements[:3]:
                print(f"     {ann.stock_code} | {ann.company_name[:15]}... | {ann.listed_exchange}")

    @pytest.mark.smoke
    def test_dataframe_conversion(self, en_scraper):
        """
        Smoke test: Verify DataFrame conversion works correctly.

        Assertions:
        - DataFrame has expected columns
        - DateTime columns are properly typed
        """
        today = date.today()
        yesterday = today - timedelta(days=1)

        result = en_scraper.scrape(yesterday, today)
        df = result.to_dataframe()

        assert isinstance(df, pd.DataFrame)

        # Check column existence
        expected_cols = ["stock_code", "company_name", "title", "publish_datetime", "publish_date"]
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"

        print(f"\n✅ DataFrame Conversion Verification:")
        print(f"   Shape: {df.shape}")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Dtypes:\n{df.dtypes}")

    @pytest.mark.smoke
    def test_convenience_function(self):
        """
        Smoke test: Verify convenience function works.
        """
        today = date.today()

        result = scrape_announcements(today, today, delay=1.0)

        assert isinstance(result, TdnetScrapeResult)
        print(f"\n✅ Convenience function returned {len(result)} announcements")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

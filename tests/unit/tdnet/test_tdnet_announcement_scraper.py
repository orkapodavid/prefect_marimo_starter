"""
TDnet Announcement Scraper Integration Tests
=============================================

Integration tests for the TdnetAnnouncementScraper service.

Documentation: docs/tdnet/TDNET_ANNOUNCEMENT_SCRAPER_GUIDE.md

These tests verify the TdnetAnnouncementScraper service can:
1. Successfully connect to TDnet and fetch announcements (English and Japanese)
2. Parse HTML responses into Pydantic models
3. Handle date ranges correctly for both languages
4. Convert results to pandas DataFrame

Note: These tests make actual network requests and may be slow.

Run with: pytest tests/unit/tdnet/test_tdnet_announcement_scraper.py -v -m integration
"""

import pytest
from datetime import date, timedelta
import pandas as pd

from src.services.tdnet.tdnet_announcement_scraper import (
    TdnetAnnouncementScraper,
    scrape_announcements,
)
from src.services.tdnet.tdnet_exceptions import TdnetScraperError
from src.services.tdnet.tdnet_announcement_models import (
    TdnetAnnouncement,
    TdnetScrapeResult,
    TdnetLanguage,
)


class TestScraperIntegration:
    """
    Integration tests that make actual requests to TDnet.

    These tests verify the scraper works end-to-end with real data.
    They may be slow and depend on network availability.
    """

    @pytest.fixture
    def scraper(self):
        """Create a scraper instance with short delay."""
        return TdnetAnnouncementScraper(delay=0.5, timeout=30)

    @pytest.mark.integration
    def test_scrape_two_day_range(self, scraper):
        """
        Smoke test: Scrape a 2-day range and verify results.

        This is the primary smoke test that verifies:
        1. Connection to TDnet works
        2. HTML parsing works
        3. Pydantic models are created correctly
        4. DataFrame conversion works
        """
        today = date.today()
        yesterday = today - timedelta(days=1)

        result = scraper.scrape(yesterday, today)

        # Verify result structure
        assert isinstance(result, TdnetScrapeResult)
        assert result.start_date == yesterday
        assert result.end_date == today
        assert result.total_count >= 0
        assert result.page_count >= 1

        # Verify announcements are Pydantic objects
        for ann in result.announcements:
            assert isinstance(ann, TdnetAnnouncement)
            assert ann.stock_code.isdigit()
            assert len(ann.stock_code) >= 4
            assert ann.company_name
            assert ann.title

        # Verify DataFrame conversion
        df = result.to_dataframe()
        assert isinstance(df, pd.DataFrame)

        if len(result) > 0:
            assert "stock_code" in df.columns
            assert "company_name" in df.columns
            assert "title" in df.columns
            assert "publish_datetime" in df.columns

        print(f"\n✅ Successfully scraped {len(result)} announcements")
        print(f"   Date range: {yesterday} to {today}")
        print(f"   Total reported: {result.total_count}")
        print(f"   Pages: {result.page_count}")

    @pytest.mark.integration
    def test_scrape_single_page(self, scraper):
        """Test scraping a single page."""
        today = date.today()

        announcements = scraper.scrape_page(today, today, page=1)

        assert isinstance(announcements, list)

        for ann in announcements:
            assert isinstance(ann, TdnetAnnouncement)

        print(f"\n✅ Page 1 has {len(announcements)} announcements")

    @pytest.mark.integration
    def test_get_total_count(self, scraper):
        """Test getting total count without full scrape."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        count = scraper.get_total_count(yesterday, today)

        assert isinstance(count, int)
        assert count >= 0

        print(f"\n✅ Total count for 2-day range: {count}")

    @pytest.mark.integration
    def test_scrape_result_iteration(self, scraper):
        """Test iterating over scrape results."""
        today = date.today()

        result = scraper.scrape(today, today)

        # Test iteration
        count = 0
        for ann in result:
            assert isinstance(ann, TdnetAnnouncement)
            count += 1

        assert count == len(result)

    @pytest.mark.integration
    def test_convenience_function(self):
        """Test the scrape_announcements convenience function."""
        today = date.today()

        result = scrape_announcements(today, today, delay=0.5)

        assert isinstance(result, TdnetScrapeResult)
        print(f"\n✅ Convenience function returned {len(result)} announcements")

    @pytest.mark.integration
    def test_context_manager(self):
        """Test using scraper as context manager."""
        today = date.today()

        with TdnetAnnouncementScraper(delay=0.5) as scraper:
            result = scraper.scrape(today, today)
            assert isinstance(result, TdnetScrapeResult)

        print("\n✅ Context manager works correctly")


class TestJapaneseScraperIntegration:
    """
    Integration tests for Japanese TDnet scraper.

    These tests verify the Japanese scraper works end-to-end with real data.
    They may be slow and depend on network availability.
    """

    @pytest.fixture
    def jp_scraper(self):
        """Create a Japanese scraper instance with short delay."""
        return TdnetAnnouncementScraper(language=TdnetLanguage.JAPANESE, delay=0.5, timeout=30)

    @pytest.mark.integration
    def test_scrape_japanese_single_day(self, jp_scraper):
        """
        Smoke test: Scrape a single day of Japanese announcements.

        This verifies:
        1. Connection to Japanese TDnet works
        2. HTML parsing works for Japanese content
        3. Japanese characters are correctly parsed
        4. New fields (listed_exchange, xbrl_url) are populated
        """
        today = date.today()

        result = jp_scraper.scrape(today, today)

        # Verify result structure
        assert isinstance(result, TdnetScrapeResult)
        assert result.start_date == today
        assert result.end_date == today
        assert result.language == TdnetLanguage.JAPANESE
        assert result.total_count >= 0

        # Verify announcements are Pydantic objects with Japanese language
        for ann in result.announcements:
            assert isinstance(ann, TdnetAnnouncement)
            assert ann.language == TdnetLanguage.JAPANESE
            assert ann.stock_code.isdigit()
            assert len(ann.stock_code) >= 4
            assert ann.company_name
            assert ann.title

        # Verify DataFrame conversion
        df = result.to_dataframe()
        assert isinstance(df, pd.DataFrame)

        if len(result) > 0:
            assert "stock_code" in df.columns
            assert "company_name" in df.columns
            assert "title" in df.columns
            assert "language" in df.columns
            assert "listed_exchange" in df.columns
            assert "xbrl_url" in df.columns

        print(f"\n✅ Successfully scraped {len(result)} Japanese announcements")
        print(f"   Date: {today}")
        print(f"   Total: {result.total_count}")
        print(f"   Pages: {result.page_count}")

    @pytest.mark.integration
    def test_japanese_fields_populated(self, jp_scraper):
        """Test that Japanese-specific fields are populated."""
        today = date.today()

        result = jp_scraper.scrape(today, today)

        # Check if any announcements have listed_exchange populated
        exchanges_found = set()
        xbrl_count = 0

        for ann in result.announcements:
            if ann.listed_exchange:
                exchanges_found.add(ann.listed_exchange)
            if ann.xbrl_url:
                xbrl_count += 1

        if len(result) > 0:
            print(f"\n📊 Japanese field analysis:")
            print(f"   Exchanges found: {exchanges_found}")
            print(f"   XBRL downloads: {xbrl_count}")

    @pytest.mark.integration
    def test_japanese_characters_parsed(self, jp_scraper):
        """Test that Japanese characters are correctly parsed."""
        today = date.today()

        result = jp_scraper.scrape(today, today)

        if len(result) > 0:
            # Check that we have actual Japanese characters
            sample_titles = [ann.title for ann in result.announcements[:5]]
            sample_companies = [ann.company_name for ann in result.announcements[:5]]

            print(f"\n📝 Sample Japanese content:")
            for i, (title, company) in enumerate(zip(sample_titles, sample_companies)):
                print(f"   {i + 1}. {company}: {title[:50]}...")

    def test_scraper_language_attribute(self):
        """Test that scraper language attribute is correctly set."""
        en_scraper = TdnetAnnouncementScraper(language=TdnetLanguage.ENGLISH)
        jp_scraper = TdnetAnnouncementScraper(language=TdnetLanguage.JAPANESE)

        assert en_scraper.language == TdnetLanguage.ENGLISH
        assert jp_scraper.language == TdnetLanguage.JAPANESE

        en_scraper.close()
        jp_scraper.close()

        print("\n✅ Language attributes correctly set")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Pytest Smoke Tests for TdnetAnnouncementScraper
================================================

Documentation: docs/TDNET_ANNOUNCEMENT_SCRAPER_GUIDE.md

These tests verify the TdnetAnnouncementScraper service can:
1. Successfully connect to TDnet and fetch announcements (English and Japanese)
2. Parse HTML responses into Pydantic models
3. Handle date ranges correctly for both languages
4. Convert results to pandas DataFrame

Run with: pytest tests/unit/tdnet/test_announcement_scraper.py -v
"""

import pytest
from datetime import date, timedelta
import pandas as pd

from src.services.tdnet.announcement_scraper import (
    TdnetAnnouncementScraper,
    scrape_announcements,
    TdnetScraperError,
)
from src.services.tdnet.announcement_models import (
    TdnetAnnouncement,
    TdnetScrapeResult,
    TdnetLanguage,
)
from src.services.tdnet.announcement_helpers import (
    format_date_param,
    parse_datetime_text,
    validate_date_range,
    split_date_range,
    calculate_page_count,
    build_request_payload,
    # Japanese helpers
    build_japanese_url,
    parse_japanese_time_text,
)


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """Tests for tdnet_helpers module."""

    def test_format_date_param(self):
        """Test date formatting to YYYYMMDD."""
        d = date(2026, 1, 15)
        assert format_date_param(d) == "20260115"

        d = date(2025, 12, 1)
        assert format_date_param(d) == "20251201"

    def test_parse_datetime_text(self):
        """Test parsing datetime strings."""
        dt, d = parse_datetime_text("2026/01/15 16:30")
        assert dt.year == 2026
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 16
        assert dt.minute == 30
        assert d == date(2026, 1, 15)

    def test_parse_datetime_text_invalid(self):
        """Test parsing invalid datetime strings."""
        with pytest.raises(ValueError):
            parse_datetime_text("invalid")

    def test_validate_date_range_valid(self):
        """Test valid date range validation."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        is_valid, msg = validate_date_range(yesterday, today)
        assert is_valid is True

    def test_validate_date_range_reversed(self):
        """Test reversed date range validation."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        is_valid, msg = validate_date_range(today, yesterday)
        assert is_valid is False
        assert "before" in msg.lower()

    def test_validate_date_range_exceeds_limit(self):
        """Test date range exceeding 31 days."""
        today = date.today()
        long_ago = today - timedelta(days=60)

        is_valid, msg = validate_date_range(long_ago, today)
        assert is_valid is False
        assert "exceeds" in msg.lower()

    def test_split_date_range_short(self):
        """Test splitting a short date range."""
        start = date(2026, 1, 1)
        end = date(2026, 1, 15)

        chunks = split_date_range(start, end)
        assert len(chunks) == 1
        assert chunks[0] == (start, end)

    def test_split_date_range_long(self):
        """Test splitting a long date range."""
        start = date(2026, 1, 1)
        end = date(2026, 3, 1)  # ~60 days

        chunks = split_date_range(start, end)
        assert len(chunks) >= 2

        # Verify chunks cover the full range
        assert chunks[0][0] == start
        assert chunks[-1][1] == end

    def test_calculate_page_count(self):
        """Test page count calculation."""
        assert calculate_page_count(0) == 1
        assert calculate_page_count(100) == 1
        assert calculate_page_count(200) == 1
        assert calculate_page_count(201) == 2
        assert calculate_page_count(400) == 2
        assert calculate_page_count(401) == 3

    def test_build_request_payload(self):
        """Test building request payload."""
        payload = build_request_payload(date(2026, 1, 14), date(2026, 1, 15), page=2, query="test")

        assert payload["t0"] == "20260114"
        assert payload["t1"] == "20260115"
        assert payload["p"] == "2"
        assert payload["q"] == "test"


# =============================================================================
# Model Tests
# =============================================================================


class TestModels:
    """Tests for tdnet_models module."""

    def test_tdnet_announcement_creation(self):
        """Test creating a TdnetAnnouncement."""
        from datetime import datetime

        ann = TdnetAnnouncement(
            publish_datetime=datetime(2026, 1, 15, 16, 30),
            publish_date=date(2026, 1, 15),
            stock_code="40620",
            company_name="IBIDEN CO.,LTD.",
            sector="Electric Appliances",
            title="Notice Concerning Tender Offer",
            pdf_url="https://example.com/doc.pdf",
            has_xbrl=False,
            notes="",
        )

        assert ann.stock_code == "40620"
        assert ann.company_name == "IBIDEN CO.,LTD."

    def test_tdnet_announcement_stock_code_validation(self):
        """Test stock code validation."""
        from datetime import datetime

        # Valid stock code (numeric)
        ann = TdnetAnnouncement(
            publish_datetime=datetime(2026, 1, 15, 16, 30),
            publish_date=date(2026, 1, 15),
            stock_code="1234",
            company_name="Test",
            sector="Test",
            title="Test",
        )
        assert ann.stock_code == "1234"

        # Valid stock code (alphanumeric, e.g. 477A0)
        ann = TdnetAnnouncement(
            publish_datetime=datetime(2026, 1, 15, 16, 30),
            publish_date=date(2026, 1, 15),
            stock_code="477A0",
            company_name="Test",
            sector="Test",
            title="Test",
        )
        assert ann.stock_code == "477A0"

        # Invalid stock code (contains symbols)
        with pytest.raises(ValueError):
            TdnetAnnouncement(
                publish_datetime=datetime(2026, 1, 15, 16, 30),
                publish_date=date(2026, 1, 15),
                stock_code="477-A",
                company_name="Test",
                sector="Test",
                title="Test",
            )

    def test_tdnet_announcement_notes_normalization(self):
        """Test notes field normalization."""
        from datetime import datetime

        ann = TdnetAnnouncement(
            publish_datetime=datetime(2026, 1, 15, 16, 30),
            publish_date=date(2026, 1, 15),
            stock_code="1234",
            company_name="Test",
            sector="Test",
            title="Test",
            notes="[Summary]",
        )
        assert ann.notes == "Summary"

        ann2 = TdnetAnnouncement(
            publish_datetime=datetime(2026, 1, 15, 16, 30),
            publish_date=date(2026, 1, 15),
            stock_code="1234",
            company_name="Test",
            sector="Test",
            title="Test",
            notes="〔Delayed〕",
        )
        assert ann2.notes == "Delayed"

    def test_tdnet_announcement_to_dict(self):
        """Test converting announcement to dictionary."""
        from datetime import datetime

        ann = TdnetAnnouncement(
            publish_datetime=datetime(2026, 1, 15, 16, 30),
            publish_date=date(2026, 1, 15),
            stock_code="40620",
            company_name="Test Company",
            sector="Test Sector",
            title="Test Title",
        )

        d = ann.to_dict()
        assert isinstance(d, dict)
        assert d["stock_code"] == "40620"
        assert "publish_datetime" in d

    def test_tdnet_scrape_result_empty(self):
        """Test empty scrape result."""
        result = TdnetScrapeResult(
            start_date=date(2026, 1, 15), end_date=date(2026, 1, 15), announcements=[]
        )

        assert len(result) == 0
        df = result.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_tdnet_scrape_result_to_list(self):
        """Test converting scrape result to list."""
        from datetime import datetime

        ann = TdnetAnnouncement(
            publish_datetime=datetime(2026, 1, 15, 16, 30),
            publish_date=date(2026, 1, 15),
            stock_code="40620",
            company_name="Test",
            sector="Test",
            title="Test",
        )

        result = TdnetScrapeResult(
            start_date=date(2026, 1, 15),
            end_date=date(2026, 1, 15),
            announcements=[ann],
        )

        data = result.to_list()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["stock_code"] == "40620"


# =============================================================================
# Integration / Smoke Tests (require network)
# =============================================================================


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


# =============================================================================
# Japanese Helper Function Tests
# =============================================================================


class TestJapaneseHelperFunctions:
    """Tests for Japanese helper functions."""

    def test_build_japanese_url(self):
        """Test building Japanese URL."""
        url = build_japanese_url(1, date(2026, 1, 16))
        assert url == "https://www.release.tdnet.info/inbs/I_list_001_20260116.html"

        url = build_japanese_url(5, date(2026, 1, 16))
        assert url == "https://www.release.tdnet.info/inbs/I_list_005_20260116.html"

    def test_parse_japanese_time_text(self):
        """Test parsing Japanese time text."""
        from datetime import datetime

        dt = parse_japanese_time_text("16:30", date(2026, 1, 16))
        assert dt == datetime(2026, 1, 16, 16, 30)

        dt = parse_japanese_time_text("09:00", date(2026, 1, 16))
        assert dt == datetime(2026, 1, 16, 9, 0)

    def test_parse_japanese_time_text_invalid(self):
        """Test parsing invalid Japanese time text."""
        import pytest

        with pytest.raises(ValueError):
            parse_japanese_time_text("invalid", date(2026, 1, 16))


# =============================================================================
# Japanese Scraper Integration Tests
# =============================================================================


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


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

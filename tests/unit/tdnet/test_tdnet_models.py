"""
TDnet Model Tests
=================

Unit tests for the TDnet Pydantic models.

Documentation: docs/tdnet/TDNET_ANNOUNCEMENT_SCRAPER_GUIDE.md
"""

import pytest
from datetime import date, datetime
import pandas as pd

from src.services.tdnet.tdnet_announcement_models import (
    TdnetAnnouncement,
    TdnetScrapeResult,
    TdnetLanguage,
)


class TestTdnetAnnouncement:
    """Tests for TdnetAnnouncement model."""

    def test_announcement_creation(self):
        """Test creating a TdnetAnnouncement."""
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

    def test_stock_code_validation_numeric(self):
        """Test stock code validation with numeric codes."""
        ann = TdnetAnnouncement(
            publish_datetime=datetime(2026, 1, 15, 16, 30),
            publish_date=date(2026, 1, 15),
            stock_code="1234",
            company_name="Test",
            sector="Test",
            title="Test",
        )
        assert ann.stock_code == "1234"

    def test_stock_code_validation_alphanumeric(self):
        """Test stock code validation with alphanumeric codes (e.g. 477A0)."""
        ann = TdnetAnnouncement(
            publish_datetime=datetime(2026, 1, 15, 16, 30),
            publish_date=date(2026, 1, 15),
            stock_code="477A0",
            company_name="Test",
            sector="Test",
            title="Test",
        )
        assert ann.stock_code == "477A0"

    def test_stock_code_validation_invalid(self):
        """Test stock code validation with invalid codes (contains symbols)."""
        with pytest.raises(ValueError):
            TdnetAnnouncement(
                publish_datetime=datetime(2026, 1, 15, 16, 30),
                publish_date=date(2026, 1, 15),
                stock_code="477-A",
                company_name="Test",
                sector="Test",
                title="Test",
            )

    def test_notes_normalization_square_brackets(self):
        """Test notes field normalization with square brackets."""
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

    def test_notes_normalization_japanese_brackets(self):
        """Test notes field normalization with Japanese brackets."""
        ann = TdnetAnnouncement(
            publish_datetime=datetime(2026, 1, 15, 16, 30),
            publish_date=date(2026, 1, 15),
            stock_code="1234",
            company_name="Test",
            sector="Test",
            title="Test",
            notes="〔Delayed〕",
        )
        assert ann.notes == "Delayed"

    def test_to_dict(self):
        """Test converting announcement to dictionary."""
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


class TestTdnetScrapeResult:
    """Tests for TdnetScrapeResult model."""

    def test_empty_result(self):
        """Test empty scrape result."""
        result = TdnetScrapeResult(
            start_date=date(2026, 1, 15), end_date=date(2026, 1, 15), announcements=[]
        )

        assert len(result) == 0
        df = result.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_to_list(self):
        """Test converting scrape result to list."""
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

    def test_iteration(self):
        """Test iterating over scrape result."""
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

        count = 0
        for item in result:
            assert isinstance(item, TdnetAnnouncement)
            count += 1

        assert count == 1

    def test_to_dataframe(self):
        """Test converting scrape result to DataFrame."""
        ann = TdnetAnnouncement(
            publish_datetime=datetime(2026, 1, 15, 16, 30),
            publish_date=date(2026, 1, 15),
            stock_code="40620",
            company_name="Test Company",
            sector="Test Sector",
            title="Test Title",
        )

        result = TdnetScrapeResult(
            start_date=date(2026, 1, 15),
            end_date=date(2026, 1, 15),
            announcements=[ann],
        )

        df = result.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "stock_code" in df.columns
        assert "company_name" in df.columns
        assert "title" in df.columns


class TestTdnetLanguage:
    """Tests for TdnetLanguage enum."""

    def test_language_values(self):
        """Test language enum values."""
        assert TdnetLanguage.ENGLISH.value == "english"
        assert TdnetLanguage.JAPANESE.value == "japanese"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

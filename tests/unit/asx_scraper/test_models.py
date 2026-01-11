"""Unit tests for ASX scraper models."""

import pytest
from services.asx_scraper.models import (
    Company,
    Announcement,
    Section8Data,
    ScrapeResult,
    ScrapeSummary
)


class TestCompanyModel:
    """Tests for Company model."""
    
    def test_company_creation(self):
        """Test creating a company model."""
        company = Company(ticker="CBA", company_name="Commonwealth Bank")
        assert company.ticker == "CBA"
        assert company.company_name == "Commonwealth Bank"
    
    def test_company_strips_whitespace(self):
        """Test that whitespace is stripped."""
        company = Company(ticker="  CBA  ", company_name="  Commonwealth Bank  ")
        assert company.ticker == "CBA"
        assert company.company_name == "Commonwealth Bank"


class TestAnnouncementModel:
    """Tests for Announcement model."""
    
    def test_announcement_creation(self):
        """Test creating an announcement model."""
        ann = Announcement(
            ticker="CBA",
            datetime="14/12/2025 8:30 PM",
            price_sensitive=True,
            headline="Capital Raising Announcement",
            pdf_url="https://example.com/doc.pdf"
        )
        assert ann.ticker == "CBA"
        assert ann.price_sensitive is True
        assert ann.headline == "Capital Raising Announcement"
    
    def test_announcement_defaults(self):
        """Test announcement default values."""
        ann = Announcement(
            ticker="CBA",
            datetime="14/12/2025 8:30 PM",
            headline="Test",
            pdf_url="https://example.com/doc.pdf"
        )
        assert ann.price_sensitive is False
        assert ann.number_of_pages is None
        assert ann.file_size is None


class TestSection8DataModel:
    """Tests for Section8Data model."""
    
    def test_section8_defaults(self):
        """Test Section8Data default values."""
        data = Section8Data()
        assert data.section_8_found is False
        assert data.item_8_6_total_available_funding is None
        assert data.item_8_7_estimated_quarters is None
        assert data.raw_section_8_text is None
    
    def test_section8_with_values(self):
        """Test Section8Data with values."""
        data = Section8Data(
            section_8_found=True,
            item_8_6_total_available_funding=1500.0,
            item_8_7_estimated_quarters=2.5
        )
        assert data.section_8_found is True
        assert data.item_8_6_total_available_funding == 1500.0
        assert data.item_8_7_estimated_quarters == 2.5
    
    def test_section8_quarters_can_be_string(self):
        """Test that estimated quarters can be a string (N/A)."""
        data = Section8Data(
            section_8_found=True,
            item_8_7_estimated_quarters="N/A"
        )
        assert data.item_8_7_estimated_quarters == "N/A"


class TestScrapeResultModel:
    """Tests for ScrapeResult model."""
    
    def test_scrape_result_creation(self):
        """Test creating a scrape result."""
        result = ScrapeResult(
            date="2025_12_14",
            stock_code="CBA",
            headline="Quarterly Report",
            pdf_link="https://example.com/doc.pdf"
        )
        assert result.date == "2025_12_14"
        assert result.stock_code == "CBA"
        assert result.pdf_downloaded is False
        assert result.extraction_success is False
    
    def test_scrape_result_with_section8(self):
        """Test scrape result with Section 8 data."""
        section8 = Section8Data(
            section_8_found=True,
            item_8_6_total_available_funding=2000.0,
            item_8_7_estimated_quarters=3.0
        )
        result = ScrapeResult(
            date="2025_12_14",
            stock_code="CBA",
            headline="Quarterly Report",
            pdf_link="https://example.com/doc.pdf",
            section_8_data=section8,
            extraction_success=True
        )
        assert result.extraction_success is True
        assert result.section_8_data.item_8_6_total_available_funding == 2000.0


class TestScrapeSummaryModel:
    """Tests for ScrapeSummary model."""
    
    def test_scrape_summary_creation(self):
        """Test creating a scrape summary."""
        summary = ScrapeSummary(
            scrape_datetime="2025-12-14T09:30:00",
            total_announcements_found=10,
            successful_extractions=8,
            warnings_count=2,
            results=[]
        )
        assert summary.total_announcements_found == 10
        assert summary.successful_extractions == 8
        assert summary.warnings_count == 2
    
    def test_scrape_summary_serialization(self):
        """Test that summary can be serialized to JSON."""
        result = ScrapeResult(
            date="2025_12_14",
            stock_code="CBA",
            headline="Test",
            pdf_link="https://example.com/doc.pdf"
        )
        summary = ScrapeSummary(
            scrape_datetime="2025-12-14T09:30:00",
            total_announcements_found=1,
            successful_extractions=1,
            warnings_count=0,
            results=[result]
        )
        json_str = summary.model_dump_json()
        assert "CBA" in json_str
        assert "2025_12_14" in json_str

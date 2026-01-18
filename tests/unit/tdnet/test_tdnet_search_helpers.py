"""
TDnet Search Helper Tests
=========================

Unit tests for the tdnet_search_helpers module functions.
"""

import pytest
from datetime import date

from src.services.tdnet.tdnet_search_helpers import (
    parse_search_results,
    extract_pdf_link,
    parse_date_str,
    extract_deal_details,
)


class TestParseSearchResults:
    """Tests for parse_search_results function."""

    def test_parse_valid_html(self, sample_search_html):
        """Test parsing valid search results HTML."""
        results = parse_search_results(sample_search_html)
        assert len(results) == 1
        assert results[0]["stock_code"] == "12340"
        assert results[0]["company_name"] == "Test Company"
        assert results[0]["title"] == "Test Title"
        assert results[0]["pdf_url"] == "test.pdf"
        assert results[0]["description"] == "Test Description"

    def test_parse_empty_html(self):
        """Test parsing empty HTML returns empty list."""
        results = parse_search_results("<html><body></body></html>")
        assert results == []

    def test_parse_no_table(self):
        """Test parsing HTML without table returns empty list."""
        results = parse_search_results("<html><body><div>No table here</div></body></html>")
        assert results == []


class TestParseDateStr:
    """Tests for parse_date_str function."""

    def test_parse_slash_format(self):
        """Test parsing YYYY/MM/DD format."""
        result = parse_date_str("2026/01/15")
        assert result == date(2026, 1, 15)

    def test_parse_dash_format(self):
        """Test parsing YYYY-MM-DD format."""
        result = parse_date_str("2026-01-15")
        assert result == date(2026, 1, 15)

    def test_parse_already_date(self):
        """Test returning date object if already a date."""
        d = date(2026, 1, 15)
        result = parse_date_str(d)
        assert result == d

    def test_parse_invalid_format(self):
        """Test parsing invalid format returns None."""
        result = parse_date_str("invalid")
        assert result is None

    def test_parse_partial_format(self):
        """Test parsing partial date returns None."""
        result = parse_date_str("2026/01")
        assert result is None


class TestExtractDealDetails:
    """Tests for extract_deal_details function."""

    def test_extract_investor(self, sample_deal_text):
        """Test extraction of investor (割当先)."""
        details = extract_deal_details(sample_deal_text)
        assert "investor" in details
        assert details["investor"] == "Test Investor"

    def test_extract_deal_size(self, sample_deal_text):
        """Test extraction of deal size (調達資金)."""
        details = extract_deal_details(sample_deal_text)
        assert "deal_size" in details
        assert details["deal_size"] == "100000000"

    def test_extract_share_price(self, sample_deal_text):
        """Test extraction of share price (発行価額)."""
        details = extract_deal_details(sample_deal_text)
        assert "share_price" in details
        assert details["share_price"] == "1000"

    def test_extract_share_count(self, sample_deal_text):
        """Test extraction of share count (発行新株式数)."""
        details = extract_deal_details(sample_deal_text)
        assert "share_count" in details
        assert details["share_count"] == "100000"

    def test_extract_deal_date(self, sample_deal_text):
        """Test extraction of deal date (払込期日)."""
        details = extract_deal_details(sample_deal_text)
        assert "deal_date" in details
        assert details["deal_date"] == "2025/1/1"

    def test_extract_deal_structure_stock(self, sample_deal_text):
        """Test extraction of deal structure for stock."""
        details = extract_deal_details(sample_deal_text)
        assert "deal_structure" in details
        assert details["deal_structure"] == "Common Stock"

    def test_extract_deal_structure_warrant(self, sample_warrant_text):
        """Test extraction of deal structure for warrants."""
        details = extract_deal_details(sample_warrant_text)
        assert details["deal_structure"] == "Warrant/Stock Option"

    def test_extract_from_empty_text(self):
        """Test extraction from empty text returns empty dict."""
        details = extract_deal_details("")
        assert details == {}

    def test_extract_from_none(self):
        """Test extraction from None returns empty dict."""
        details = extract_deal_details(None)
        assert details == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

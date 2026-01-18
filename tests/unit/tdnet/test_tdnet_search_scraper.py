"""
TDnet Search Scraper Unit Tests
================================

Unit tests for the TdnetSearchScraper class.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import shutil
from datetime import date, datetime
from src.services.tdnet.tdnet_search_scraper import TdnetSearchScraper
from src.services.tdnet.tdnet_search_models import TdnetSearchEntry, TdnetSearchResult
from src.services.tdnet.tdnet_search_helpers import (
    parse_search_results,
    extract_deal_details,
    parse_date_str,
)


class TestTdnetSearchScraper(unittest.TestCase):
    """Unit tests for TdnetSearchScraper."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = "test_output_tdnet"
        self.scraper = TdnetSearchScraper(output_dir=self.test_dir, download_pdfs=False)

    def tearDown(self):
        """Clean up test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("src.services.tdnet.tdnet_search_scraper.requests.Session.get")
    def test_fetch_page(self, mock_get):
        """Test fetching a search results page."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><table></table></body></html>"
        mock_get.return_value = mock_response

        # Test private method _fetch_page
        html = self.scraper._fetch_page("test query", 1)
        self.assertEqual(html, "<html><body><table></table></body></html>")

    def test_parse_results(self):
        """Test parsing search results HTML using helper function."""
        html = """
        <html><body><table>
        <tr>
            <td>2025/01/01 10:00</td>
            <td>12340</td>
            <td>Test Company</td>
            <td><a href="test.pdf">Test Title</a></td>
        </tr>
        <tr>
            <td colspan="4">Test Description</td>
        </tr>
        </table></body></html>
        """
        results = parse_search_results(html)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["stock_code"], "12340")
        self.assertEqual(results[0]["company_name"], "Test Company")
        self.assertEqual(results[0]["title"], "Test Title")
        self.assertEqual(results[0]["pdf_url"], "test.pdf")
        self.assertEqual(results[0]["description"], "Test Description")

    def test_extract_deal_details(self):
        """Test extracting deal details from PDF text using helper function."""
        text = """
        割当先：Test Investor
        調達資金：100,000,000円
        発行価額：1,000円
        発行新株式数：100,000株
        払込期日：2025年1月1日
        新株式発行
        """
        details = extract_deal_details(text)
        self.assertEqual(details["investor"], "Test Investor")
        self.assertEqual(details["deal_size"], "100000000")
        self.assertEqual(details["share_price"], "1000")
        self.assertEqual(details["share_count"], "100000")
        self.assertEqual(details["deal_date"], "2025/1/1")
        self.assertEqual(details["deal_structure"], "Common Stock")

    @patch("src.services.tdnet.tdnet_search_scraper.TdnetSearchScraper._fetch_page")
    def test_scrape(self, mock_fetch):
        """Test full scrape workflow."""
        # Mock HTML response
        html = """
        <html><body><table>
        <tr>
            <td>2025/01/01 10:00</td>
            <td>12340</td>
            <td>Test Company</td>
            <td><a href="test.pdf">Test Title</a></td>
        </tr>
        </table></body></html>
        """
        # Return HTML for first call, then None to stop pagination
        mock_fetch.side_effect = [
            html,
            None,
            html,
            None,
            html,
            None,
            html,
            None,
            html,
            None,
            html,
            None,
        ]
        # We have multiple tiers/terms.
        # tier1: 2 terms
        # tier2: 2 terms
        # tier3: 1 term
        # Total 5 terms. Each needs 1 page + 1 stop.

        # Run scrape
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 1)
        result = self.scraper.scrape(start_date, end_date)

        self.assertIsInstance(result, TdnetSearchResult)
        self.assertEqual(
            len(result.entries), 1
        )  # Will likely be more because of multiple tiers matching same mocked HTML
        # Since we loop through 3 tiers, and mock_fetch returns the same HTML for all, we might get duplicates if logic doesn't handle them or different tiers.
        # But the scraper handles duplicates by key.
        # So we should get 1 entry.

        entry = result.entries[0]
        self.assertIsInstance(entry, TdnetSearchEntry)
        self.assertEqual(entry.stock_code, "12340")
        self.assertEqual(entry.tier, "Tier 1 (95%+)")  # First tier processed


class TestParseDateStr(unittest.TestCase):
    """Unit tests for parse_date_str helper function."""

    def test_slash_format(self):
        """Test parsing YYYY/MM/DD format."""
        result = parse_date_str("2026/01/15")
        self.assertEqual(result, date(2026, 1, 15))

    def test_dash_format(self):
        """Test parsing YYYY-MM-DD format."""
        result = parse_date_str("2026-01-15")
        self.assertEqual(result, date(2026, 1, 15))

    def test_already_date(self):
        """Test returning date object if already a date."""
        d = date(2026, 1, 15)
        result = parse_date_str(d)
        self.assertEqual(result, d)

    def test_invalid_format(self):
        """Test parsing invalid format returns None."""
        result = parse_date_str("invalid")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

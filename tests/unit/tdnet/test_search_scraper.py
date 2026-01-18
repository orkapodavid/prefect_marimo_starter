import unittest
from unittest.mock import MagicMock, patch
import os
import shutil
from datetime import date, datetime
from src.services.tdnet.search_scraper import TdnetSearchScraper
from src.services.tdnet.search_models import TdnetSearchEntry, TdnetSearchResult


class TestTdnetSearchScraper(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_output_tdnet"
        self.scraper = TdnetSearchScraper(output_dir=self.test_dir, download_pdfs=False)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("src.services.tdnet.search_scraper.requests.Session.get")
    def test_fetch_page(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><table></table></body></html>"
        mock_get.return_value = mock_response

        # Test private method _fetch_page
        html = self.scraper._fetch_page("test query", 1)
        self.assertEqual(html, "<html><body><table></table></body></html>")

    def test_parse_results(self):
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
        results = self.scraper._parse_results(html)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["stock_code"], "12340")
        self.assertEqual(results[0]["company_name"], "Test Company")
        self.assertEqual(results[0]["title"], "Test Title")
        self.assertEqual(results[0]["pdf_link"], "test.pdf")
        self.assertEqual(results[0]["description"], "Test Description")

    def test_extract_deal_details(self):
        text = """
        割当先：Test Investor
        調達資金：100,000,000円
        発行価額：1,000円
        発行新株式数：100,000株
        払込期日：2025年1月1日
        新株式発行
        """
        details = self.scraper._extract_deal_details(text)
        self.assertEqual(details["investor"], "Test Investor")
        self.assertEqual(details["deal_size"], "100000000")
        self.assertEqual(details["share_price"], "1000")
        self.assertEqual(details["share_count"], "100000")
        self.assertEqual(details["deal_date"], "2025/1/1")
        self.assertEqual(details["deal_structure"], "Common Stock")

    @patch("src.services.tdnet.search_scraper.TdnetSearchScraper._fetch_page")
    def test_scrape(self, mock_fetch):
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


if __name__ == "__main__":
    unittest.main()

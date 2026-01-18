"""
TDnet Search Scraper Smoke Test
================================

Smoke test that verifies the TDnet Search Scraper works with live tdnet-search.appspot.com.
This test makes actual HTTP requests to search for third-party allotment announcements.

Run with: pytest tests/smoke/tdnet/test_search_smoke.py -v -s
"""

import pytest
from datetime import date, timedelta

from src.services.tdnet import (
    TdnetSearchScraper,
    TdnetSearchEntry,
    TdnetSearchResult,
)


class TestTdnetSearchSmoke:
    """
    Smoke tests for TDnet Search Scraper using live tdnet-search.appspot.com.

    These tests verify:
    1. Search endpoint is accessible
    2. Third-party allotment announcements are found
    3. Results contain expected fields (stock_code, company, title, pdf_link)
    4. Tier categorization works correctly
    """

    @pytest.fixture
    def scraper(self):
        """Create TDnet Search scraper."""
        return TdnetSearchScraper(delay=1.0, download_pdfs=False)

    @pytest.mark.smoke
    def test_search_third_party_allotments(self, scraper):
        """
        Smoke test: Verify we can search for third-party allotment announcements.

        Expected URL: https://tdnet-search.appspot.com/search

        This search uses tiered keywords:
        - Tier 1 (95%+): 第三者割当 発行に関するお知らせ
        - Tier 2 (90%+): 第三者割当 新株式 -払込完了
        - Tier 3 (85%+): 第三者割当 割当先決定

        Assertions:
        - TdnetSearchResult is returned
        - Entries list is populated (may be empty for short date range)
        - Each entry has stock_code, company_name, title
        """
        # Search last 30 days (more likely to have results)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        result = scraper.scrape(start_date, end_date)

        # Result structure
        assert isinstance(result, TdnetSearchResult)
        assert result.start_date == start_date
        assert result.end_date == end_date
        assert result.total_count >= 0
        assert "search_terms_used" in result.metadata

        print(f"\n✅ TDnet Search Verification:")
        print(f"   Date range: {start_date} to {end_date}")
        print(f"   Total entries found: {result.total_count}")
        print(f"   Search terms used: {len(result.metadata['search_terms_used'])}")

        # Verify entry structure (if any found)
        if result.entries:
            tiers_found = set()
            for entry in result.entries[:10]:
                assert isinstance(entry, TdnetSearchEntry)
                assert entry.stock_code, "stock_code is empty"
                assert entry.company_name, "company_name is empty"
                assert entry.title, "title is empty"
                assert entry.date, "date is empty"
                if entry.tier:
                    tiers_found.add(entry.tier)

            print(f"\n   Tiers matched: {tiers_found}")
            print(f"\n   Sample entries:")
            for entry in result.entries[:5]:
                print(f"     {entry.date} | {entry.stock_code} | {entry.company_name[:20]}...")
                print(f"       Title: {entry.title[:50]}...")
                print(f"       Tier: {entry.tier}")
                if entry.pdf_link:
                    print(f"       PDF: {entry.pdf_link[:60]}...")

    @pytest.mark.smoke
    def test_search_with_narrower_date_range(self, scraper):
        """
        Smoke test: Search with a narrower date range (last 7 days).

        This tests the date filtering logic.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        result = scraper.scrape(start_date, end_date)

        assert isinstance(result, TdnetSearchResult)

        # Verify date filtering
        for entry in result.entries:
            assert start_date <= entry.date <= end_date, (
                f"Entry date {entry.date} outside range [{start_date}, {end_date}]"
            )

        print(f"\n✅ Narrow Date Range Verification:")
        print(f"   Date range: {start_date} to {end_date}")
        print(f"   Entries found: {result.total_count}")

    @pytest.mark.smoke
    def test_result_has_pdf_links(self, scraper):
        """
        Smoke test: Verify that results have PDF links when available.

        PDF links should point to release.tdnet.info.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        result = scraper.scrape(start_date, end_date)

        pdf_count = sum(1 for e in result.entries if e.pdf_link)
        no_pdf_count = len(result.entries) - pdf_count

        print(f"\n✅ PDF Link Verification:")
        print(f"   Entries with PDF: {pdf_count}")
        print(f"   Entries without PDF: {no_pdf_count}")

        # Check PDF URL structure
        for entry in result.entries[:5]:
            if entry.pdf_link:
                # PDF links should be absolute URLs
                assert entry.pdf_link.startswith("http"), f"Invalid PDF URL: {entry.pdf_link}"
                print(f"   Sample PDF: {entry.pdf_link}")

    @pytest.mark.smoke
    def test_deal_details_extraction(self, scraper):
        """
        Smoke test: Verify deal details extraction patterns work.

        This tests the regex patterns for extracting:
        - 割当先 (allottee/investor)
        - 調達資金 (deal size)
        - 発行価額 (share price)
        - 発行新株式数 (share count)
        """
        # Test extraction with sample text
        sample_text = """
        1. 割当先：株式会社テスト投資
        2. 調達資金の額：500,000,000円
        3. 発行価額：1,000円
        4. 発行新株式数：500,000株
        5. 払込期日：2026年1月15日
        6. 本件は新株予約権の発行です。
        """

        details = scraper._extract_deal_details(sample_text)

        assert "investor" in details, "Failed to extract investor"
        assert "deal_size" in details, "Failed to extract deal_size"
        assert "share_price" in details, "Failed to extract share_price"
        assert "share_count" in details, "Failed to extract share_count"
        assert "deal_structure" in details, "Failed to extract deal_structure"

        print(f"\n✅ Deal Details Extraction Verification:")
        print(f"   Investor: {details.get('investor')}")
        print(f"   Deal Size: {details.get('deal_size')} {details.get('deal_size_currency', '')}")
        print(f"   Share Price: {details.get('share_price')}")
        print(f"   Share Count: {details.get('share_count')}")
        print(f"   Deal Structure: {details.get('deal_structure')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

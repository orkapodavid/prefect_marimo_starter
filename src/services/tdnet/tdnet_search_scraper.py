"""
TDnet Search Scraper
====================

Scraper for third-party allotment (第三者割当) announcements from TDnet Search.
Target: https://tdnet-search.appspot.com/search

Usage:
    scraper = TdnetSearchScraper(download_pdfs=True, output_dir="./pdfs")
    result = scraper.scrape(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
"""

import time
import os
import logging
import requests
from datetime import date
from typing import List, Optional, Set

from .tdnet_search_models import TdnetSearchEntry, TdnetSearchResult
from .tdnet_search_constants import BASE_URL, SEARCH_TERMS, TIER_MAPPING
from .tdnet_search_helpers import (
    parse_search_results,
    download_and_extract_pdf,
    extract_deal_details,
    HAS_PYPDF,
)

# Configure logging
logger = logging.getLogger(__name__)


class TdnetSearchScraper:
    """
    Scraper for TDnet Search (tdnet-search.appspot.com).

    This scraper uses tiered search terms to find third-party allotment
    announcements with varying precision levels.

    Attributes:
        delay: Seconds to wait between requests (default: 1.0)
        download_pdfs: Whether to download and extract PDFs (default: False)
        output_dir: Directory to save downloaded PDFs (default: ".")

    Example:
        >>> scraper = TdnetSearchScraper(delay=1.0)
        >>> result = scraper.scrape(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
        >>> print(f"Found {result.total_count} entries")
    """

    def __init__(self, delay: float = 1.0, download_pdfs: bool = False, output_dir: str = "."):
        """
        Initialize the TDnet Search Scraper.

        Args:
            delay: Seconds to wait between requests (default: 1.0)
            download_pdfs: Whether to download and extract PDFs (default: False)
            output_dir: Directory to save downloaded PDFs (default: ".")
        """
        self.delay = delay
        self.download_pdfs = download_pdfs
        self.output_dir = output_dir

        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

        if self.download_pdfs:
            os.makedirs(self.output_dir, exist_ok=True)

    def scrape(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> TdnetSearchResult:
        """
        Scrape announcements for a date range using tiered search terms.

        Args:
            start_date: Start of date range (optional)
            end_date: End of date range (optional)

        Returns:
            TdnetSearchResult containing all found entries
        """
        all_entries: List[TdnetSearchEntry] = []
        seen_keys: Set[str] = set()
        metadata = {"search_terms_used": []}

        logger.info(f"Starting scrape for range: {start_date} to {end_date}")

        for tier_name, terms in SEARCH_TERMS.items():
            logger.info(f"Processing {tier_name}")

            for term_info in terms:
                query = term_info["query"]
                metadata["search_terms_used"].append(query)
                logger.info(f"Searching: {query}")

                page = 1
                consecutive_empty = 0
                max_pages = 100  # Safety limit

                while page <= max_pages:
                    html = self._fetch_page(query, page)
                    if not html:
                        break

                    results = parse_search_results(html)

                    if not results:
                        consecutive_empty += 1
                        if consecutive_empty >= 2:
                            break
                        page += 1
                        continue

                    consecutive_empty = 0

                    # Filter by date
                    valid_results = []
                    if start_date and end_date:
                        # Check if page has data older than start_date to stop early
                        page_dates = []
                        for r in results:
                            d = r.get("publish_date")
                            if d:
                                page_dates.append(d)

                        if page_dates and max(page_dates) < start_date:
                            logger.info(
                                f"Reached data before start date on page {page}. Stopping query."
                            )
                            break

                        for r in results:
                            d = r.get("publish_date")
                            if d and start_date <= d <= end_date:
                                valid_results.append(r)
                    else:
                        valid_results = results

                    for res_dict in valid_results:
                        # Unique key: datetime + stock_code + title
                        key = f"{res_dict['publish_datetime']}_{res_dict['stock_code']}_{res_dict['title']}"
                        if key not in seen_keys:
                            seen_keys.add(key)

                            # Enhance with tier
                            res_dict["tier"] = TIER_MAPPING.get(tier_name, "Unknown")

                            # Create model
                            try:
                                entry = TdnetSearchEntry(**res_dict)

                                # PDF Extraction
                                if self.download_pdfs and entry.pdf_url and HAS_PYPDF:
                                    pdf_text = download_and_extract_pdf(
                                        self.session,
                                        entry.pdf_url,
                                        entry.doc_id,
                                        self.output_dir,
                                    )
                                    if pdf_text:
                                        entry.pdf_downloaded = True
                                        details = extract_deal_details(pdf_text)
                                        # Update entry with details
                                        for k, v in details.items():
                                            setattr(entry, k, v)

                                all_entries.append(entry)
                            except Exception as e:
                                logger.error(f"Failed to create entry model: {e}")

                    page += 1
                    time.sleep(self.delay)

        return TdnetSearchResult(
            start_date=start_date,
            end_date=end_date,
            entries=all_entries,
            total_count=len(all_entries),
            metadata=metadata,
        )

    def _fetch_page(self, query: str, page: int) -> Optional[str]:
        """Fetch a single search results page."""
        try:
            params = {"query": query, "page": page}
            resp = self.session.get(BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.error(f"Error fetching page {page} for query '{query}': {e}")
            return None

    def _extract_deal_details(self, text: str):
        """
        Extract deal details from PDF text.

        This method is kept for backward compatibility with tests.
        Delegates to the helper function.
        """
        return extract_deal_details(text)


# --- CLI / Main Block ---
if __name__ == "__main__":
    # Simple CLI for testing
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1, help="Days back to scrape")
    args = parser.parse_args()

    end = date.today()
    start = end  # Just today for default, or implement timedelta logic

    print(f"Scraping {start} to {end}...")
    scraper = TdnetSearchScraper()
    result = scraper.scrape(start, end)
    print(f"Found {result.total_count} entries.")
    for entry in result.entries[:5]:
        print(f"- {entry.publish_date} {entry.company_name}: {entry.title}")

#!/usr/bin/env python3
"""
TDnet Announcement Scraper Service
===================================

Documentation: docs/TDNET_ANNOUNCEMENT_SCRAPER_GUIDE.md

Usage:
    from TdnetAnnouncementScraper import TdnetAnnouncementScraper
    from datetime import date

    scraper = TdnetAnnouncementScraper()
    result = scraper.scrape(date(2026, 1, 14), date(2026, 1, 15))
    df = result.to_dataframe()
"""

import time
import logging
from datetime import date, datetime
from typing import Optional, List, Callable

import requests
from requests.exceptions import RequestException

from .announcement_models import TdnetAnnouncement, TdnetScrapeResult, TdnetLanguage
from .announcement_helpers import (
    TDNET_SEARCH_ENDPOINT,
    MAX_DATE_RANGE_DAYS,
    build_request_payload,
    parse_announcements_from_html,
    extract_total_count,
    calculate_page_count,
    validate_date_range,
    split_date_range,
    get_request_headers,
    # Japanese helpers
    build_japanese_url,
    parse_japanese_announcements_from_html,
    get_japanese_request_headers,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TdnetScraperError(Exception):
    """Base exception for TDnet scraper errors."""

    pass


class TdnetRequestError(TdnetScraperError):
    """Raised when a request to TDnet fails."""

    pass


class TdnetParseError(TdnetScraperError):
    """Raised when parsing TDnet HTML fails."""

    pass


class TdnetAnnouncementScraper:
    """
    Service for scraping TDnet Company Announcements.

    This scraper fetches announcements from the TDnet Company Announcements
    Service in either English or Japanese, parsing the HTML and returning
    structured Pydantic models.

    Attributes:
        language: Language to scrape (ENGLISH or JAPANESE)
        delay: Seconds to wait between requests (default: 1.0)
        timeout: Request timeout in seconds (default: 30)
        max_retries: Maximum retry attempts for failed requests (default: 3)

    Example:
        >>> # English scraping (default)
        >>> scraper = TdnetAnnouncementScraper()
        >>> result = scraper.scrape(date(2026, 1, 14), date(2026, 1, 15))
        >>>
        >>> # Japanese scraping
        >>> jp_scraper = TdnetAnnouncementScraper(language=TdnetLanguage.JAPANESE)
        >>> result = jp_scraper.scrape(date(2026, 1, 16), date(2026, 1, 16))
        >>> df = result.to_dataframe()
    """

    def __init__(
        self,
        language: TdnetLanguage = TdnetLanguage.ENGLISH,
        delay: float = 1.0,
        timeout: int = 30,
        max_retries: int = 3,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ):
        """
        Initialize the TDnet Announcement Scraper.

        Args:
            language: Language to scrape (ENGLISH or JAPANESE)
            delay: Seconds to wait between requests (default: 1.0)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts for failed requests (default: 3)
            on_progress: Optional callback for progress updates (page, total_pages)
        """
        self.language = language
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.on_progress = on_progress

        self.session = requests.Session()
        # Set headers based on language
        if language == TdnetLanguage.JAPANESE:
            self.session.headers.update(get_japanese_request_headers())
        else:
            self.session.headers.update(get_request_headers())

    def scrape(
        self, start_date: date, end_date: date, query: str = ""
    ) -> TdnetScrapeResult:
        """
        Scrape announcements for a date range.

        For English: If the date range exceeds 31 days, it will be automatically
        split into chunks and scraped sequentially.

        For Japanese: Scrapes each day individually as the Japanese site uses
        per-day URLs.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            query: Optional search query to filter results (English only)

        Returns:
            TdnetScrapeResult: Result containing all announcements

        Raises:
            TdnetScraperError: If scraping fails after all retries

        Example:
            >>> result = scraper.scrape(date(2026, 1, 14), date(2026, 1, 15))
            >>> print(f"Total: {result.total_count}, Scraped: {len(result)}")
        """
        # Validate date range
        is_valid, message = validate_date_range(start_date, end_date)
        if not is_valid and "exceeds" not in message:
            raise ValueError(message)

        # Dispatch based on language
        if self.language == TdnetLanguage.JAPANESE:
            return self._scrape_japanese(start_date, end_date)

        # English scraping
        days_diff = (end_date - start_date).days
        if days_diff > MAX_DATE_RANGE_DAYS:
            logger.info(
                f"Date range ({days_diff} days) exceeds limit, splitting into chunks"
            )
            return self._scrape_english_chunked(start_date, end_date, query)

        return self._scrape_english_range(start_date, end_date, query)

    def _scrape_english_chunked(
        self, start_date: date, end_date: date, query: str = ""
    ) -> TdnetScrapeResult:
        """Scrape a date range by splitting into chunks (English only)."""
        chunks = split_date_range(start_date, end_date)
        logger.info(f"Split into {len(chunks)} chunks")

        all_announcements: List[TdnetAnnouncement] = []
        total_count = 0
        total_pages = 0

        for i, (chunk_start, chunk_end) in enumerate(chunks, 1):
            logger.info(
                f"Scraping chunk {i}/{len(chunks)}: {chunk_start} to {chunk_end}"
            )

            chunk_result = self._scrape_english_range(chunk_start, chunk_end, query)
            all_announcements.extend(chunk_result.announcements)
            total_count += chunk_result.total_count
            total_pages += chunk_result.page_count

            # Delay between chunks
            if i < len(chunks):
                time.sleep(self.delay)

        return TdnetScrapeResult(
            start_date=start_date,
            end_date=end_date,
            query=query,
            total_count=total_count,
            page_count=total_pages,
            announcements=all_announcements,
            scraped_at=datetime.now(),
            language=TdnetLanguage.ENGLISH,
        )

    def _scrape_english_range(
        self, start_date: date, end_date: date, query: str = ""
    ) -> TdnetScrapeResult:
        """Scrape a single date range (max 31 days) - English only."""
        # First request to get total count
        first_page_html = self._fetch_page(start_date, end_date, 1, query)
        total_count = extract_total_count(first_page_html)
        page_count = calculate_page_count(total_count)

        logger.info(f"Found {total_count} announcements across {page_count} pages")

        # Parse first page
        all_announcements = self._parse_page(first_page_html)

        if self.on_progress:
            self.on_progress(1, page_count)

        # Fetch remaining pages
        for page in range(2, page_count + 1):
            time.sleep(self.delay)

            html = self._fetch_page(start_date, end_date, page, query)
            page_announcements = self._parse_page(html)
            all_announcements.extend(page_announcements)

            logger.info(
                f"Scraped page {page}/{page_count} ({len(page_announcements)} items)"
            )

            if self.on_progress:
                self.on_progress(page, page_count)

        return TdnetScrapeResult(
            start_date=start_date,
            end_date=end_date,
            query=query,
            total_count=total_count,
            page_count=page_count,
            announcements=all_announcements,
            scraped_at=datetime.now(),
            language=TdnetLanguage.ENGLISH,
        )

    def scrape_page(
        self, start_date: date, end_date: date, page: int = 1, query: str = ""
    ) -> List[TdnetAnnouncement]:
        """
        Scrape a single page of announcements.

        Useful for testing or when you only need a subset of results.

        Args:
            start_date: Start of date range
            end_date: End of date range
            page: Page number (1-indexed)
            query: Optional search query

        Returns:
            List[TdnetAnnouncement]: Announcements from the specified page

        Example:
            >>> announcements = scraper.scrape_page(date(2026, 1, 15), date(2026, 1, 15), 1)
            >>> print(f"Page 1 has {len(announcements)} items")
        """
        html = self._fetch_page(start_date, end_date, page, query)
        return self._parse_page(html)

    def _fetch_page(
        self, start_date: date, end_date: date, page: int, query: str = ""
    ) -> str:
        """Fetch a single page with retry logic."""
        payload = build_request_payload(start_date, end_date, page, query)

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.post(
                    TDNET_SEARCH_ENDPOINT, data=payload, timeout=self.timeout
                )
                response.raise_for_status()
                return response.text
            except RequestException as e:
                last_error = e
                logger.warning(
                    f"Request failed (attempt {attempt}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries:
                    time.sleep(self.delay * attempt)  # Exponential backoff

        raise TdnetRequestError(
            f"Failed to fetch page {page} after {self.max_retries} attempts: {last_error}"
        )

    def _parse_page(self, html: str) -> List[TdnetAnnouncement]:
        """Parse HTML and return list of announcements."""
        try:
            raw_data = parse_announcements_from_html(html)
            announcements = []

            for data in raw_data:
                try:
                    announcement = TdnetAnnouncement(**data)
                    announcements.append(announcement)
                except Exception as e:
                    logger.warning(f"Failed to parse announcement: {e}")
                    continue

            return announcements
        except Exception as e:
            raise TdnetParseError(f"Failed to parse page HTML: {e}")

    # =========================================================================
    # Japanese Scraping Methods
    # =========================================================================

    def _scrape_japanese(self, start_date: date, end_date: date) -> TdnetScrapeResult:
        """
        Scrape Japanese TDnet announcements for a date range.

        The Japanese site uses per-day URLs, so we loop through each day
        and scrape all pages for that day.
        """
        from datetime import timedelta

        all_announcements: List[TdnetAnnouncement] = []
        total_pages = 0
        current_date = start_date

        while current_date <= end_date:
            logger.info(f"Scraping Japanese announcements for {current_date}")

            day_announcements, pages = self._scrape_japanese_day(current_date)
            all_announcements.extend(day_announcements)
            total_pages += pages

            current_date += timedelta(days=1)

            # Delay between days
            if current_date <= end_date:
                time.sleep(self.delay)

        return TdnetScrapeResult(
            start_date=start_date,
            end_date=end_date,
            query="",  # Japanese doesn't support query
            total_count=len(all_announcements),
            page_count=total_pages,
            announcements=all_announcements,
            scraped_at=datetime.now(),
            language=TdnetLanguage.JAPANESE,
        )

    def _scrape_japanese_day(
        self, target_date: date
    ) -> tuple[List[TdnetAnnouncement], int]:
        """
        Scrape all pages of Japanese announcements for a single day.

        Returns:
            Tuple of (list of announcements, number of pages scraped)
        """
        all_announcements: List[TdnetAnnouncement] = []
        page = 1

        while True:
            try:
                html = self._fetch_japanese_page(target_date, page)
                page_announcements = self._parse_japanese_page(html, target_date)

                if not page_announcements:
                    # No more announcements on this page
                    break

                all_announcements.extend(page_announcements)
                logger.info(
                    f"Scraped JP page {page} for {target_date} "
                    f"({len(page_announcements)} items)"
                )

                if self.on_progress:
                    self.on_progress(page, page)  # We don't know total pages

                page += 1
                time.sleep(self.delay)

            except TdnetRequestError as e:
                # 404 means no more pages for this day
                if "404" in str(e):
                    break
                raise

        return all_announcements, page - 1

    def _fetch_japanese_page(self, target_date: date, page: int) -> str:
        """Fetch a single Japanese page with retry logic."""
        url = build_japanese_url(page, target_date)

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)

                # 404 means no more pages
                if response.status_code == 404:
                    raise TdnetRequestError(f"404: No page {page} for {target_date}")

                response.raise_for_status()
                # The page uses UTF-8 encoding
                response.encoding = "utf-8"
                return response.text

            except RequestException as e:
                last_error = e
                logger.warning(
                    f"Japanese request failed (attempt {attempt}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries:
                    time.sleep(self.delay * attempt)

        raise TdnetRequestError(
            f"Failed to fetch Japanese page {page} for {target_date} "
            f"after {self.max_retries} attempts: {last_error}"
        )

    def _parse_japanese_page(
        self, html: str, publication_date: date
    ) -> List[TdnetAnnouncement]:
        """Parse Japanese HTML and return list of announcements."""
        try:
            raw_data = parse_japanese_announcements_from_html(html, publication_date)
            announcements = []

            for data in raw_data:
                try:
                    # Add language field for Japanese
                    data["language"] = TdnetLanguage.JAPANESE
                    announcement = TdnetAnnouncement(**data)
                    announcements.append(announcement)
                except Exception as e:
                    logger.warning(f"Failed to parse Japanese announcement: {e}")
                    continue

            return announcements
        except Exception as e:
            raise TdnetParseError(f"Failed to parse Japanese page HTML: {e}")

    def get_total_count(self, start_date: date, end_date: date, query: str = "") -> int:
        """
        Get the total announcement count without scraping all pages.

        Useful for estimating scrape time or checking if there are results.

        Args:
            start_date: Start of date range
            end_date: End of date range
            query: Optional search query

        Returns:
            int: Total number of announcements

        Example:
            >>> count = scraper.get_total_count(date(2026, 1, 15), date(2026, 1, 15))
            >>> print(f"Today has {count} announcements")
        """
        html = self._fetch_page(start_date, end_date, 1, query)
        return extract_total_count(html)

    def close(self):
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience function for quick scraping
def scrape_announcements(
    start_date: date,
    end_date: date,
    query: str = "",
    delay: float = 1.0,
    language: TdnetLanguage = TdnetLanguage.ENGLISH,
) -> TdnetScrapeResult:
    """
    Convenience function to scrape TDnet announcements.

    Args:
        start_date: Start of date range
        end_date: End of date range
        query: Optional search query (English only)
        delay: Seconds between requests
        language: Language to scrape (ENGLISH or JAPANESE)

    Returns:
        TdnetScrapeResult: Scraping result

    Example:
        >>> from TdnetAnnouncementScraper import scrape_announcements
        >>> result = scrape_announcements(date(2026, 1, 14), date(2026, 1, 15))
        >>> df = result.to_dataframe()
        >>>
        >>> # Japanese scraping
        >>> result = scrape_announcements(
        ...     date(2026, 1, 16), date(2026, 1, 16),
        ...     language=TdnetLanguage.JAPANESE
        ... )
    """
    with TdnetAnnouncementScraper(language=language, delay=delay) as scraper:
        return scraper.scrape(start_date, end_date, query)


if __name__ == "__main__":
    # Example usage
    from datetime import timedelta

    today = date.today()
    yesterday = today - timedelta(days=1)

    print(f"Scraping announcements from {yesterday} to {today}")

    scraper = TdnetAnnouncementScraper(delay=1.0)
    result = scraper.scrape(yesterday, today)

    print("\nResults:")
    print(f"  Total count: {result.total_count}")
    print(f"  Pages scraped: {result.page_count}")
    print(f"  Announcements: {len(result.announcements)}")

    if result.announcements:
        print("\nFirst announcement:")
        ann = result.announcements[0]
        print(f"  Date: {ann.publish_datetime}")
        print(f"  Company: {ann.company_name} ({ann.stock_code})")
        print(f"  Title: {ann.title[:80]}...")

    # Convert to DataFrame
    df = result.to_dataframe()
    print(f"\nDataFrame shape: {df.shape}")
    print(df.head())

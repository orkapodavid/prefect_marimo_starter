"""
FEFTA Crawler Service
=====================

A helper service for crawling and parsing FEFTA (Foreign Exchange and Foreign
Trade Act) company classification data from the Japanese Ministry of Finance.

Usage:
    from services.fefta import FeftaCrawler

    crawler = FeftaCrawler()
    source, records = crawler.run()

Documentation: Based on docs/FEFTA_Crawler_Implementation_Prompt.md
"""

import time
import logging
from datetime import date
from pathlib import Path
from typing import List, Tuple, Optional

import httpx
import pandas as pd
from bs4 import BeautifulSoup

from .fefta_models import (
    FeftaSource,
    FeftaRecord,
    FeftaCrawlerError,
    FeftaLinkNotFoundError,
)
from .fefta_constants import (
    DEFAULT_BASE_URL,
    DEFAULT_USER_AGENT,
    DEFAULT_OUTPUT_DIR,
)
from .fefta_helpers import find_fefta_links
from .fefta_excel_parser import parse_fefta_excel

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# FeftaCrawler Class
# =============================================================================


class FeftaCrawler:
    """
    Service for crawling FEFTA company classification data from MOF.

    This crawler:
    1. Fetches the MOF "Related Guidance and Documents" page
    2. Locates the latest FEFTA Excel link by "As of" date
    3. Downloads the Excel file with a date-prefixed filename
    4. Parses the company records from the designated sheet

    Attributes:
        base_url: URL of the MOF page containing FEFTA links
        output_dir: Directory to save downloaded Excel files
        timeout: HTTP request timeout in seconds
        max_retries: Maximum retry attempts for HTTP requests

    Example:
        >>> crawler = FeftaCrawler()
        >>> source, records = crawler.run()
        >>> print(f"Found {len(records)} companies as of {source.as_of_date}")
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        output_dir: Optional[Path] = None,
        timeout: int = 20,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        user_agent: Optional[str] = None,
    ):
        """
        Initialize the FEFTA Crawler.

        Args:
            base_url: URL of the MOF page containing FEFTA links
            output_dir: Directory to save downloaded Excel files
            timeout: HTTP request timeout in seconds
            max_retries: Maximum retry attempts for HTTP requests
            retry_delay: Base delay between retries (exponential backoff)
            user_agent: Custom User-Agent header (optional)
        """
        self.base_url = base_url
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.user_agent = user_agent or DEFAULT_USER_AGENT

        # Create HTTP client with custom headers
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
        )

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    # =========================================================================
    # Public API
    # =========================================================================

    def fetch_latest_source(self) -> FeftaSource:
        """
        Fetch the MOF page and locate the latest FEFTA Excel link.

        Returns:
            FeftaSource: Metadata about the Excel source (saved_path not set)

        Raises:
            FeftaCrawlerError: If page fetch fails
            FeftaLinkNotFoundError: If no FEFTA Excel link is found
            FeftaDateParseError: If date cannot be parsed from link text
        """
        logger.info(f"Fetching MOF page: {self.base_url}")
        html = self._fetch_with_retry(self.base_url)

        # Parse HTML and find FEFTA links
        soup = BeautifulSoup(html, "html.parser")
        fefta_links = find_fefta_links(soup, self.base_url)

        if not fefta_links:
            raise FeftaLinkNotFoundError(f"No FEFTA Excel links found on page: {self.base_url}")

        # Choose the link with the latest "As of" date
        latest_link = max(fefta_links, key=lambda x: x["as_of_date"])

        logger.info(
            f"Found FEFTA link: {latest_link['link_text'][:80]}... "
            f"(As of: {latest_link['as_of_date']})"
        )

        return FeftaSource(
            as_of_raw=latest_link["as_of_raw"],
            as_of_date=latest_link["as_of_date"],
            download_date=date.today(),
            file_url=latest_link["file_url"],
            saved_path=None,
        )

    def download_excel(self, source: FeftaSource) -> FeftaSource:
        """
        Download the Excel file and save with a date-prefixed filename.

        Args:
            source: FeftaSource with file_url to download

        Returns:
            FeftaSource: Updated with saved_path set

        Raises:
            FeftaCrawlerError: If download fails
        """
        # Ensure output directory exists
        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Extract original filename from URL
        original_filename = source.file_url.split("/")[-1]

        # Create date-prefixed filename
        today_prefix = date.today().strftime("%Y_%m_%d")
        new_filename = f"{today_prefix}_{original_filename}"
        save_path = output_dir / new_filename

        logger.info(f"Downloading Excel from: {source.file_url}")
        content = self._fetch_with_retry(source.file_url, as_bytes=True)

        # Save to file
        save_path.write_bytes(content)
        logger.info(f"Saved Excel to: {save_path.absolute()}")

        # Return updated source with saved_path
        return FeftaSource(
            as_of_raw=source.as_of_raw,
            as_of_date=source.as_of_date,
            download_date=source.download_date,
            file_url=source.file_url,
            saved_path=str(save_path.absolute()),
        )

    def parse_records(self, saved_path: str) -> Tuple[List[FeftaRecord], pd.DataFrame]:
        """
        Parse the FEFTA Excel file and extract company records.

        Args:
            saved_path: Absolute path to the downloaded Excel file

        Returns:
            Tuple of (list of FeftaRecord, raw DataFrame)

        Raises:
            FeftaExcelParseError: If parsing fails
        """
        return parse_fefta_excel(saved_path)

    def run(self) -> Tuple[FeftaSource, List[FeftaRecord]]:
        """
        End-to-end orchestration: fetch source → download → parse.

        Returns:
            Tuple of (FeftaSource with all fields populated, list of FeftaRecord)

        Example:
            >>> crawler = FeftaCrawler()
            >>> source, records = crawler.run()
            >>> print(f"Downloaded {len(records)} records")
        """
        # Step 1: Fetch latest source info
        source = self.fetch_latest_source()

        # Step 2: Download the Excel file
        source = self.download_excel(source)

        # Step 3: Parse records
        records, _ = self.parse_records(source.saved_path)

        return source, records

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _fetch_with_retry(self, url: str, as_bytes: bool = False) -> str | bytes:
        """
        Fetch a URL with retry logic and exponential backoff.

        Args:
            url: URL to fetch
            as_bytes: If True, return bytes instead of text

        Returns:
            Response content as string or bytes

        Raises:
            FeftaCrawlerError: If all retries fail
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.get(url)
                response.raise_for_status()

                if as_bytes:
                    return response.content
                return response.text

            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Request failed (attempt {attempt}/{self.max_retries}): {e}")

                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    time.sleep(delay)

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"HTTP error {e.response.status_code} (attempt {attempt}/{self.max_retries})"
                )

                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    time.sleep(delay)

        raise FeftaCrawlerError(
            f"Failed to fetch {url} after {self.max_retries} attempts: {last_error}"
        )

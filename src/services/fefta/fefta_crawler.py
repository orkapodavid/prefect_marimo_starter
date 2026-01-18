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

import re
import time
import logging
from datetime import date
from pathlib import Path
from typing import List, Tuple, Optional
from urllib.parse import urljoin

import httpx
import pandas as pd
from bs4 import BeautifulSoup

from .fefta_models import (
    FeftaSource,
    FeftaRecord,
    FeftaCrawlerError,
    FeftaLinkNotFoundError,
    FeftaDateParseError,
    FeftaExcelParseError,
)
from .fefta_constants import (
    DEFAULT_BASE_URL,
    DEFAULT_USER_AGENT,
    DEFAULT_OUTPUT_DIR,
    MONTH_MAP,
    CIRCLED_NUMERAL_MAP,
    SHEET_NAME,
    COLUMN_MAPPINGS,
)

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
        fefta_links = self._find_fefta_links(soup)

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
        logger.info(f"Parsing Excel file: {saved_path}")

        try:
            # Read the Excel file with specific sheet
            df = pd.read_excel(
                saved_path,
                sheet_name=SHEET_NAME,
                dtype=str,  # Read all as strings to preserve leading zeros
                engine="openpyxl",
            )
        except ValueError as e:
            if SHEET_NAME in str(e):
                raise FeftaExcelParseError(
                    f"Sheet '{SHEET_NAME}' not found in Excel file. "
                    f"Available sheets may have different names."
                )
            raise FeftaExcelParseError(f"Failed to read Excel file: {e}")
        except Exception as e:
            raise FeftaExcelParseError(f"Failed to read Excel file: {e}")

        # Map columns to our field names
        column_map = self._map_columns(df.columns.tolist())

        # Rename columns
        df_mapped = df.rename(columns=column_map)

        # Parse records, skipping empty/header rows
        records = []
        skipped_rows = 0
        for idx, row in df_mapped.iterrows():
            # Check if this is an empty or header row by looking at key fields
            securities_code = str(row.get("securities_code", "")).strip()
            isin_code = str(row.get("isin_code", "")).strip()

            # Skip rows where both securities_code and isin_code are empty/nan
            if (
                not securities_code
                or securities_code == "nan"
                or not isin_code
                or isin_code == "nan"
            ):
                skipped_rows += 1
                logger.debug(f"Skipping row {idx}: empty securities_code or isin_code")
                continue

            try:
                record = self._parse_row(row, idx)
                records.append(record)
            except FeftaExcelParseError as e:
                # Log warning and skip row if it can't be parsed
                # This handles edge cases like partial data rows
                logger.warning(f"Skipping row {idx}: {e}")
                skipped_rows += 1
                continue

        logger.info(f"Parsed {len(records)} records from Excel (skipped {skipped_rows} rows)")
        return records, df

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

    def _find_fefta_links(self, soup: BeautifulSoup) -> List[dict]:
        """
        Find all FEFTA Excel links on the page.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            List of dicts with: link_text, file_url, as_of_raw, as_of_date
        """
        fefta_links = []

        # Find all anchor tags
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "")
            link_text = anchor.get_text(strip=True)

            # Check if it's a FEFTA Excel link
            if "FEFTA" in link_text and href.endswith(".xlsx"):
                # Parse the "As of" date from link text
                try:
                    as_of_raw, as_of_date = self._parse_as_of_date(link_text)
                except FeftaDateParseError:
                    logger.warning(f"Could not parse date from link: {link_text[:80]}...")
                    continue

                # Convert relative URL to absolute
                file_url = urljoin(self.base_url, href)

                fefta_links.append(
                    {
                        "link_text": link_text,
                        "file_url": file_url,
                        "as_of_raw": as_of_raw,
                        "as_of_date": as_of_date,
                    }
                )

        return fefta_links

    def _parse_as_of_date(self, link_text: str) -> Tuple[str, date]:
        """
        Parse the "As of" date from link text.

        Args:
            link_text: Full text of the anchor element

        Returns:
            Tuple of (raw as_of text, parsed date)

        Raises:
            FeftaDateParseError: If date cannot be parsed
        """
        # Pattern: "As of DD Month, YYYY" or "As of DD Month YYYY"
        pattern = r"As of (\d{1,2})\s+([A-Za-z]+),?\s*(\d{4})"
        match = re.search(pattern, link_text)

        if not match:
            raise FeftaDateParseError(f"Could not find 'As of' date pattern in: {link_text}")

        day_str, month_name, year_str = match.groups()

        # Parse month
        month_key = month_name.lower()
        if month_key not in MONTH_MAP:
            raise FeftaDateParseError(f"Unknown month name '{month_name}' in: {link_text}")

        month = MONTH_MAP[month_key]
        day = int(day_str)
        year = int(year_str)

        # Build the raw string
        as_of_raw = f"As of {day} {month_name}, {year}"

        return as_of_raw, date(year, month, day)

    def _map_columns(self, columns: List[str]) -> dict:
        """
        Map Excel column names to our field names.

        Args:
            columns: List of column names from the Excel file

        Returns:
            Dict mapping original column names to our field names

        Raises:
            FeftaExcelParseError: If required columns are missing
        """
        column_map = {}
        missing_fields = []

        for field_name, search_terms in COLUMN_MAPPINGS.items():
            found = False
            for col in columns:
                for term in search_terms:
                    if term in col:
                        column_map[col] = field_name
                        found = True
                        break
                if found:
                    break

            if not found:
                missing_fields.append(field_name)

        if missing_fields:
            raise FeftaExcelParseError(
                f"Missing required columns: {missing_fields}. Available columns: {columns}"
            )

        return column_map

    def _parse_row(self, row: pd.Series, row_idx: int) -> FeftaRecord:
        """
        Parse a single row into a FeftaRecord.

        Args:
            row: Pandas Series representing the row
            row_idx: Row index for error messages

        Returns:
            FeftaRecord instance

        Raises:
            FeftaExcelParseError: If parsing fails
        """
        # Normalize circled numerals for category (required)
        category = self._normalize_circled_numeral(row.get("category", ""), row_idx, "category")

        # core_operator is optional - may be empty for non-core companies
        core_operator = self._normalize_circled_numeral_optional(
            row.get("core_operator", ""), row_idx, "core_operator"
        )

        return FeftaRecord(
            securities_code=str(row.get("securities_code", "")),
            isin_code=str(row.get("isin_code", "")),
            company_name_ja=str(row.get("company_name_ja", "")),
            issue_or_company_name=str(row.get("issue_or_company_name", "")),
            category=category,
            core_operator=core_operator,
        )

    def _normalize_circled_numeral(self, value: str, row_idx: int, column_name: str) -> int:
        """
        Convert a circled numeral or plain digit to an integer.

        Args:
            value: String value that may contain circled numeral or digit
            row_idx: Row index for error messages
            column_name: Column name for error messages

        Returns:
            Integer value (1-10)

        Raises:
            FeftaExcelParseError: If value cannot be normalized
        """
        if pd.isna(value) or value is None:
            raise FeftaExcelParseError(f"Empty value in column '{column_name}' at row {row_idx}")

        value_str = str(value).strip()

        if not value_str:
            raise FeftaExcelParseError(f"Empty value in column '{column_name}' at row {row_idx}")

        # Check if it's a circled numeral
        if value_str in CIRCLED_NUMERAL_MAP:
            return CIRCLED_NUMERAL_MAP[value_str]

        # Try to parse as a plain integer
        try:
            result = int(float(value_str))
            if 1 <= result <= 10:
                return result
            raise FeftaExcelParseError(
                f"Value {result} out of range (1-10) in column '{column_name}' at row {row_idx}"
            )
        except (ValueError, TypeError):
            pass

        raise FeftaExcelParseError(
            f"Cannot normalize value '{value_str}' in column '{column_name}' "
            f"at row {row_idx}. Expected circled numeral (①-⑩) or integer (1-10)."
        )

    def _normalize_circled_numeral_optional(
        self, value: str, row_idx: int, column_name: str
    ) -> Optional[int]:
        """
        Convert a circled numeral or plain digit to an integer, allowing None.

        Unlike _normalize_circled_numeral, this returns None for empty values
        instead of raising an error.

        Args:
            value: String value that may contain circled numeral, digit, or be empty
            row_idx: Row index for error messages
            column_name: Column name for error messages

        Returns:
            Integer value (1-10) or None if empty/na
        """
        # Check for empty/na values - return None instead of raising error
        if pd.isna(value) or value is None:
            return None

        value_str = str(value).strip()

        # Empty string or dash means not applicable
        if not value_str or value_str == "-" or value_str == "－":
            return None

        # Check if it's a circled numeral
        if value_str in CIRCLED_NUMERAL_MAP:
            return CIRCLED_NUMERAL_MAP[value_str]

        # Try to parse as a plain integer
        try:
            result = int(float(value_str))
            if 1 <= result <= 10:
                return result
            # Out of range - log warning but return None
            logger.warning(
                f"Value {result} out of range (1-10) in column '{column_name}' "
                f"at row {row_idx}, treating as None"
            )
            return None
        except (ValueError, TypeError):
            pass

        # Unrecognized value - log warning but return None
        logger.warning(
            f"Cannot normalize value '{value_str}' in column '{column_name}' "
            f"at row {row_idx}, treating as None"
        )
        return None

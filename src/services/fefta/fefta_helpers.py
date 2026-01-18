"""
FEFTA Helper Functions
======================

Pure helper functions for parsing FEFTA data from MOF website.
These functions are stateless and can be tested independently.
"""

import re
import logging
from datetime import date
from typing import List, Tuple, Optional
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup

from .fefta_models import (
    FeftaDateParseError,
    FeftaExcelParseError,
)
from .fefta_constants import (
    MONTH_MAP,
    CIRCLED_NUMERAL_MAP,
    COLUMN_MAPPINGS,
)

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Link and Date Parsing
# =============================================================================


def parse_as_of_date(link_text: str) -> Tuple[str, date]:
    """
    Parse the "As of" date from link text.

    Args:
        link_text: Full text of the anchor element

    Returns:
        Tuple of (raw as_of text, parsed date)

    Raises:
        FeftaDateParseError: If date cannot be parsed

    Example:
        >>> parse_as_of_date('FEFTA (As of 15 July, 2025)(Excel:296KB)')
        ('As of 15 July, 2025', date(2025, 7, 15))
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


def find_fefta_links(soup: BeautifulSoup, base_url: str) -> List[dict]:
    """
    Find all FEFTA Excel links on the page.

    Args:
        soup: BeautifulSoup parsed HTML
        base_url: Base URL for resolving relative hrefs

    Returns:
        List of dicts with: link_text, file_url, as_of_raw, as_of_date

    Example:
        >>> from bs4 import BeautifulSoup
        >>> html = '<a href="file.xlsx">FEFTA (As of 15 July, 2025)</a>'
        >>> soup = BeautifulSoup(html, 'html.parser')
        >>> links = find_fefta_links(soup, 'https://example.com/')
        >>> len(links)
        1
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
                as_of_raw, as_of_date = parse_as_of_date(link_text)
            except FeftaDateParseError:
                logger.warning(f"Could not parse date from link: {link_text[:80]}...")
                continue

            # Convert relative URL to absolute
            file_url = urljoin(base_url, href)

            fefta_links.append(
                {
                    "link_text": link_text,
                    "file_url": file_url,
                    "as_of_raw": as_of_raw,
                    "as_of_date": as_of_date,
                }
            )

    return fefta_links


# =============================================================================
# Circled Numeral Normalization
# =============================================================================


def normalize_circled_numeral(value: str, row_idx: int, column_name: str) -> int:
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

    Example:
        >>> normalize_circled_numeral('①', 0, 'category')
        1
        >>> normalize_circled_numeral('5', 0, 'category')
        5
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


def normalize_circled_numeral_optional(value: str, row_idx: int, column_name: str) -> Optional[int]:
    """
    Convert a circled numeral or plain digit to an integer, allowing None.

    Unlike normalize_circled_numeral, this returns None for empty values
    instead of raising an error.

    Args:
        value: String value that may contain circled numeral, digit, or be empty
        row_idx: Row index for error messages
        column_name: Column name for error messages

    Returns:
        Integer value (1-10) or None if empty/na

    Example:
        >>> normalize_circled_numeral_optional('①', 0, 'core_operator')
        1
        >>> normalize_circled_numeral_optional('', 0, 'core_operator')
        None
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


# =============================================================================
# Column Mapping
# =============================================================================


def map_columns(columns: List[str]) -> dict:
    """
    Map Excel column names to our field names.

    Args:
        columns: List of column names from the Excel file

    Returns:
        Dict mapping original column names to our field names

    Raises:
        FeftaExcelParseError: If required columns are missing

    Example:
        >>> cols = ['証券コード (Securities code)', 'ISINコード (ISIN code)']
        >>> mapping = map_columns(cols)
        >>> 'securities_code' in mapping.values()
        True
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

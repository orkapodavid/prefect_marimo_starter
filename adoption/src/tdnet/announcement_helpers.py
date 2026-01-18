"""
TDnet Scraper Helper Functions
==============================

Helper functions for the TdnetAnnouncementScraper service.

Documentation: docs/TDNET_ANNOUNCEMENT_SCRAPER_GUIDE.md

This module provides utility functions for:
- Date formatting and parsing
- HTML parsing and data extraction
- Request payload building
- Validation and error handling
"""

import re
import math
from datetime import datetime, date, timedelta
from typing import Optional, Tuple, List, Dict, Any
from bs4 import BeautifulSoup, Tag

# Constants - English
TDNET_BASE_URL = "https://www.release.tdnet.info"
TDNET_SEARCH_ENDPOINT = f"{TDNET_BASE_URL}/onsf/TDJFSearch_e/TDJFSearch_e"
ITEMS_PER_PAGE = 200
MAX_DATE_RANGE_DAYS = 31
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Constants - Japanese
TDNET_JP_BASE_URL = f"{TDNET_BASE_URL}/inbs"
JP_ITEMS_PER_PAGE = 100


def format_date_param(d: date) -> str:
    """
    Convert a date object to TDnet's YYYYMMDD format.

    Args:
        d: Date to format

    Returns:
        str: Date string in YYYYMMDD format

    Example:
        >>> format_date_param(date(2026, 1, 15))
        '20260115'
    """
    return d.strftime("%Y%m%d")


def parse_datetime_text(text: str) -> Tuple[datetime, date]:
    """
    Parse TDnet datetime text to datetime and date objects.

    Args:
        text: Datetime string in "YYYY/MM/DD HH:MM" format

    Returns:
        Tuple[datetime, date]: Parsed datetime and date objects

    Raises:
        ValueError: If the text cannot be parsed

    Example:
        >>> dt, d = parse_datetime_text("2026/01/15 16:30")
        >>> dt
        datetime(2026, 1, 15, 16, 30)
    """
    text = text.strip()
    try:
        dt = datetime.strptime(text, "%Y/%m/%d %H:%M")
        return dt, dt.date()
    except ValueError:
        # Try date-only format
        try:
            dt = datetime.strptime(text, "%Y/%m/%d")
            return dt, dt.date()
        except ValueError:
            raise ValueError(f"Cannot parse datetime: {text}")


def extract_total_count(html: str) -> int:
    """
    Extract the total announcement count from HTML.

    Args:
        html: HTML content of the page

    Returns:
        int: Total number of announcements, or 0 if not found

    Example:
        >>> extract_total_count('<div>Total 1722 Announcements</div>')
        1722
    """
    match = re.search(r"Total\s+(\d+)\s+Announcements?", html, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def calculate_page_count(total: int, per_page: int = ITEMS_PER_PAGE) -> int:
    """
    Calculate the number of pages needed for pagination.

    Args:
        total: Total number of items
        per_page: Items per page (default: 200)

    Returns:
        int: Number of pages (minimum 1)

    Example:
        >>> calculate_page_count(450)
        3
    """
    if total <= 0:
        return 1
    return math.ceil(total / per_page)


def build_request_payload(
    start_date: date, end_date: date, page: int = 1, query: str = ""
) -> Dict[str, str]:
    """
    Build the POST request payload for TDnet search.

    Args:
        start_date: Start of date range
        end_date: End of date range
        page: Page number (1-indexed)
        query: Optional search query

    Returns:
        Dict[str, str]: Request payload dictionary

    Example:
        >>> payload = build_request_payload(date(2026, 1, 14), date(2026, 1, 15), 1)
        >>> payload
        {'t0': '20260114', 't1': '20260115', 'q': '', 'p': '1'}
    """
    return {
        "t0": format_date_param(start_date),
        "t1": format_date_param(end_date),
        "q": query,
        "p": str(page),
    }


def parse_announcement_row(row: Tag) -> Optional[Dict[str, Any]]:
    """
    Parse a single table row into announcement data.

    Args:
        row: BeautifulSoup Tag representing a table row

    Returns:
        Optional[Dict[str, Any]]: Parsed data or None if row is invalid

    Example:
        >>> soup = BeautifulSoup(html, 'html.parser')
        >>> row = soup.find('tr')
        >>> data = parse_announcement_row(row)
    """
    cells = row.find_all("td")
    if len(cells) < 7:
        return None

    try:
        # Extract datetime
        time_text = cells[0].get_text(strip=True)
        if not time_text or "/" not in time_text:
            return None

        publish_datetime, publish_date = parse_datetime_text(time_text)

        # Extract stock code
        stock_code = cells[1].get_text(strip=True)
        if not stock_code or not stock_code.isdigit():
            return None

        # Extract company name
        company_name = cells[2].get_text(strip=True)

        # Extract sector
        sector = cells[3].get_text(strip=True)

        # Extract title and PDF URL
        title_cell = cells[4]
        title = title_cell.get_text(strip=True)
        pdf_link = title_cell.find("a", href=True)
        pdf_url = pdf_link["href"] if pdf_link else None

        # Extract XBRL indicator
        xbrl_text = cells[5].get_text(strip=True)
        has_xbrl = bool(xbrl_text)

        # Extract notes
        notes = cells[6].get_text(strip=True)

        return {
            "publish_datetime": publish_datetime,
            "publish_date": publish_date,
            "stock_code": stock_code,
            "company_name": company_name,
            "sector": sector,
            "title": title,
            "pdf_url": pdf_url,
            "has_xbrl": has_xbrl,
            "notes": notes,
        }
    except Exception:
        return None


def parse_announcements_from_html(html: str) -> List[Dict[str, Any]]:
    """
    Parse all announcements from an HTML page.

    Args:
        html: HTML content of the page

    Returns:
        List[Dict[str, Any]]: List of parsed announcement dictionaries

    Example:
        >>> announcements = parse_announcements_from_html(response.text)
        >>> len(announcements)
        200
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find the main data table
    table = soup.find("table", id="maintable")
    if not table:
        # Fallback: try to find any table with the eng class
        table = soup.find("table", class_="eng")

    if not table:
        return []

    rows = table.find_all("tr")
    announcements = []

    for row in rows:
        data = parse_announcement_row(row)
        if data:
            announcements.append(data)

    return announcements


def validate_date_range(start_date: date, end_date: date) -> Tuple[bool, str]:
    """
    Validate a date range for TDnet scraping.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Tuple[bool, str]: (is_valid, message)

    Example:
        >>> valid, msg = validate_date_range(date(2026, 1, 1), date(2026, 1, 15))
        >>> valid
        True
    """
    if start_date > end_date:
        return False, "Start date must be before or equal to end date"

    if end_date > date.today():
        return False, "End date cannot be in the future"

    days_diff = (end_date - start_date).days
    if days_diff > MAX_DATE_RANGE_DAYS:
        return (
            False,
            f"Date range exceeds {MAX_DATE_RANGE_DAYS} days (got {days_diff} days)",
        )

    return True, "Valid date range"


def split_date_range(
    start_date: date, end_date: date, chunk_days: int = MAX_DATE_RANGE_DAYS
) -> List[Tuple[date, date]]:
    """
    Split a date range into chunks of maximum size.

    Args:
        start_date: Start of date range
        end_date: End of date range
        chunk_days: Maximum days per chunk (default: 31)

    Returns:
        List[Tuple[date, date]]: List of (start, end) date tuples

    Example:
        >>> chunks = split_date_range(date(2026, 1, 1), date(2026, 3, 1))
        >>> len(chunks)
        2
    """
    chunks = []
    current_start = start_date

    while current_start <= end_date:
        current_end = min(current_start + timedelta(days=chunk_days - 1), end_date)
        chunks.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)

    return chunks


def get_request_headers() -> Dict[str, str]:
    """
    Get default HTTP headers for TDnet requests.

    Returns:
        Dict[str, str]: Headers dictionary
    """
    return {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": TDNET_BASE_URL,
        "Referer": f"{TDNET_BASE_URL}/onsf/TDJFSearch_e/I_head",
    }


# =============================================================================
# Japanese TDnet Helper Functions
# =============================================================================


def build_japanese_url(page: int, target_date: date) -> str:
    """
    Build the URL for a Japanese TDnet announcements page.

    Args:
        page: Page number (1-indexed)
        target_date: Date to fetch announcements for

    Returns:
        str: Full URL to the announcements page

    Example:
        >>> build_japanese_url(1, date(2026, 1, 16))
        'https://www.release.tdnet.info/inbs/I_list_001_20260116.html'
    """
    date_str = format_date_param(target_date)
    return f"{TDNET_JP_BASE_URL}/I_list_{page:03d}_{date_str}.html"


def parse_japanese_time_text(time_text: str, publication_date: date) -> datetime:
    """
    Parse Japanese TDnet time text (HH:MM) to full datetime.

    The Japanese table only shows time, so we combine with the known date.

    Args:
        time_text: Time string in "HH:MM" format
        publication_date: The date of the announcement

    Returns:
        datetime: Full datetime combining date and time

    Raises:
        ValueError: If the time cannot be parsed

    Example:
        >>> parse_japanese_time_text("16:30", date(2026, 1, 16))
        datetime(2026, 1, 16, 16, 30)
    """
    time_text = time_text.strip()
    try:
        time_obj = datetime.strptime(time_text, "%H:%M")
        return datetime.combine(publication_date, time_obj.time())
    except ValueError:
        raise ValueError(f"Cannot parse Japanese time: {time_text}")


def parse_japanese_announcement_row(
    row: Tag, publication_date: date
) -> Optional[Dict[str, Any]]:
    """
    Parse a single table row from Japanese TDnet into announcement data.

    The Japanese table has 7 columns:
    1. Time (時刻) - HH:MM format
    2. Code (コード) - Stock code
    3. Company Name (会社名) - Company name in Japanese
    4. Title (表題) - Announcement title with PDF link
    5. XBRL - Link to XBRL zip file if available
    6. Listed Exchange (上場取引所) - Exchange abbreviation (東, 名, etc.)
    7. Update History (更新履歴) - Update status

    Args:
        row: BeautifulSoup Tag representing a table row
        publication_date: Date of the announcement (row only has time)

    Returns:
        Optional[Dict[str, Any]]: Parsed data or None if row is invalid

    Example:
        >>> soup = BeautifulSoup(html, 'html.parser')
        >>> row = soup.find('tr')
        >>> data = parse_japanese_announcement_row(row, date(2026, 1, 16))
    """
    cells = row.find_all("td")
    if len(cells) < 7:
        return None

    try:
        # Column 0: Time (e.g., "16:30")
        time_text = cells[0].get_text(strip=True)
        if not time_text or ":" not in time_text:
            return None

        publish_datetime = parse_japanese_time_text(time_text, publication_date)

        # Column 1: Stock Code
        stock_code = cells[1].get_text(strip=True)
        if not stock_code or not stock_code.isdigit():
            return None

        # Column 2: Company Name (may have trailing whitespace)
        company_name = cells[2].get_text(strip=True)
        if not company_name:
            return None

        # Column 3: Title with PDF link
        title_cell = cells[3]
        title = title_cell.get_text(strip=True)
        pdf_link = title_cell.find("a", href=True)
        pdf_url = None
        if pdf_link:
            href = pdf_link["href"]
            # Make absolute URL if relative
            if not href.startswith("http"):
                pdf_url = f"{TDNET_JP_BASE_URL}/{href}"
            else:
                pdf_url = href

        # Column 4: XBRL link
        xbrl_cell = cells[4]
        xbrl_link = xbrl_cell.find("a", href=True)
        xbrl_url = None
        has_xbrl = False
        if xbrl_link:
            has_xbrl = True
            href = xbrl_link["href"]
            if not href.startswith("http"):
                xbrl_url = f"{TDNET_JP_BASE_URL}/{href}"
            else:
                xbrl_url = href

        # Column 5: Listed Exchange (東, 名, etc.)
        listed_exchange = cells[5].get_text(strip=True)

        # Column 6: Update History (訂正, 取消, etc.)
        update_history = cells[6].get_text(strip=True)
        # Convert update history to notes format
        notes = update_history if update_history else ""

        return {
            "publish_datetime": publish_datetime,
            "publish_date": publication_date,
            "stock_code": stock_code,
            "company_name": company_name,
            "title": title,
            "pdf_url": pdf_url,
            "has_xbrl": has_xbrl,
            "notes": notes,
            "listed_exchange": listed_exchange,
            "xbrl_url": xbrl_url,
        }
    except Exception:
        return None


def parse_japanese_announcements_from_html(
    html: str, publication_date: date
) -> List[Dict[str, Any]]:
    """
    Parse all announcements from a Japanese TDnet HTML page.

    Args:
        html: HTML content of the page
        publication_date: Date of the announcements

    Returns:
        List[Dict[str, Any]]: List of parsed announcement dictionaries

    Example:
        >>> announcements = parse_japanese_announcements_from_html(response.text, date(2026, 1, 16))
        >>> len(announcements)
        100
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find the main data table by ID
    table = soup.find("table", id="main-list-table")
    if not table:
        # Fallback: try to find table by class
        table = soup.find("table", class_="main-list-table")

    if not table:
        return []

    rows = table.find_all("tr")
    announcements = []

    for row in rows:
        # Skip header rows (they use th instead of td)
        if row.find("th"):
            continue

        data = parse_japanese_announcement_row(row, publication_date)
        if data:
            announcements.append(data)

    return announcements


def get_japanese_request_headers() -> Dict[str, str]:
    """
    Get HTTP headers for Japanese TDnet requests.

    Returns:
        Dict[str, str]: Headers dictionary
    """
    return {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": f"{TDNET_JP_BASE_URL}/I_main_00.html",
    }

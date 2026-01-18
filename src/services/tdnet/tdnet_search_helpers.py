"""
TDnet Search Helper Functions
=============================

Helper functions for the TDnet Search Scraper service.

Documentation: docs/tdnet/TDNET_SEARCH_OPTIMIZATION.md

This module provides utility functions for:
- HTML parsing and result extraction
- PDF link extraction
- Date string parsing
- PDF download and text extraction
- Deal details extraction from PDF text
"""

import re
import os
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Try importing pypdf
try:
    from pypdf import PdfReader

    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


def parse_search_results(html: str) -> List[Dict[str, Any]]:
    """
    Parse TDnet Search HTML response into a list of result dictionaries.

    Args:
        html: Raw HTML response from tdnet-search.appspot.com

    Returns:
        List of dictionaries containing parsed announcement data

    Example:
        >>> results = parse_search_results(response.text)
        >>> for r in results:
        ...     print(r['title'])
    """
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    table = soup.find("table")
    if not table:
        return entries

    rows = table.find_all("tr")
    i = 0
    while i < len(rows):
        row = rows[i]
        cells = row.find_all("td")

        # Skip separator rows
        if len(cells) == 1 and cells[0].get("colspan") == "4":
            i += 1
            continue

        if len(cells) >= 4:
            try:
                datetime_text = cells[0].get_text(strip=True)
                stock_code = cells[1].get_text(strip=True)
                company_name = cells[2].get_text(strip=True)
                title_cell = cells[3]

                # Date parsing
                date_obj = parse_date_str(datetime_text.split()[0])
                if not date_obj:
                    i += 1
                    continue

                title_link = title_cell.find("a")
                if title_link:
                    title = title_link.get_text(strip=True)
                    pdf_link = extract_pdf_link(row)
                else:
                    title = title_cell.get_text(strip=True)
                    pdf_link = None

                doc_id = "N/A"
                if pdf_link:
                    doc_id = pdf_link.split("/")[-1].replace(".pdf", "")

                # Description (next row)
                description = None
                if i + 1 < len(rows):
                    next_row = rows[i + 1]
                    next_cells = next_row.find_all("td")
                    if len(next_cells) == 1 and next_cells[0].get("colspan") == "4":
                        desc_text = next_cells[0].get_text(strip=True)
                        description = desc_text[:200] if desc_text else None
                        i += 1

                entries.append(
                    {
                        "publish_datetime": datetime_text,
                        "publish_date": date_obj,
                        "stock_code": stock_code,
                        "company_name": company_name,
                        "title": title,
                        "pdf_url": pdf_link,
                        "description": description,
                        "doc_id": doc_id,
                    }
                )
            except Exception as e:
                logger.warning(f"Error parsing row: {e}")
        i += 1
    return entries


def extract_pdf_link(row) -> Optional[str]:
    """
    Extract PDF URL from a table row element.

    Args:
        row: BeautifulSoup Tag representing a table row

    Returns:
        PDF URL string or None if not found

    Example:
        >>> pdf_url = extract_pdf_link(row_tag)
        >>> if pdf_url:
        ...     print(f"PDF: {pdf_url}")
    """
    links = row.find_all("a")
    for link in links:
        href = link.get("href", "")
        if "pdf" in href.lower() or "release.tdnet.info" in href:
            return href
    return None


def parse_date_str(date_str: str) -> Optional[date]:
    """
    Parse YYYY/MM/DD or YYYY-MM-DD string to date object.

    Args:
        date_str: Date string in YYYY/MM/DD or YYYY-MM-DD format

    Returns:
        date object or None if parsing fails

    Example:
        >>> parse_date_str("2026/01/15")
        date(2026, 1, 15)
        >>> parse_date_str("2026-01-15")
        date(2026, 1, 15)
    """
    if isinstance(date_str, date):
        return date_str
    try:
        # Try YYYY/MM/DD
        return datetime.strptime(date_str, "%Y/%m/%d").date()
    except ValueError:
        try:
            # Try YYYY-MM-DD
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None


def download_and_extract_pdf(session, url: str, doc_id: str, output_dir: str) -> Optional[str]:
    """
    Download a PDF and extract its text content.

    Args:
        session: requests.Session object for making HTTP requests
        url: URL of the PDF to download
        doc_id: Document ID for naming the saved file
        output_dir: Directory to save the downloaded PDF

    Returns:
        Extracted text from the PDF or None if extraction fails

    Note:
        Requires pypdf library to be installed for text extraction.
    """
    if not HAS_PYPDF:
        return None
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()

        pdf_path = os.path.join(output_dir, f"{doc_id}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(resp.content)

        with open(pdf_path, "rb") as f:
            reader = PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        logger.warning(f"PDF extract failed for {doc_id}: {e}")
        return None


def extract_deal_details(text: str) -> Dict[str, Any]:
    """
    Extract deal details from PDF text using regex patterns.

    Extracts the following fields:
    - investor: 割当先 (allottee/investor)
    - deal_size: 調達資金 (fund raising amount)
    - deal_size_currency: Currency unit
    - share_price: 発行価額 (issue price)
    - share_count: 発行新株式数 (number of shares)
    - deal_date: 払込期日/割当日/発行日 (payment/allotment/issue date)
    - deal_structure: Type of deal (Stock, Warrant, Convertible Bond)

    Args:
        text: Raw text extracted from PDF

    Returns:
        Dictionary containing extracted deal details

    Example:
        >>> details = extract_deal_details(pdf_text)
        >>> print(details.get('investor'))
        '株式会社テスト投資'
    """
    if not text:
        return {}
    details = {}

    investor = re.search(r"割当先[\s：:]*([^\n\r]+)", text)
    if investor:
        details["investor"] = investor.group(1).strip()

    size = re.search(r"調達資金[^0-9]*([0-9,]+).*?([百千万億円]+)", text)
    if size:
        details["deal_size"] = size.group(1).replace(",", "")
        details["deal_size_currency"] = size.group(2)

    price = re.search(r"発行価額[^0-9]*([0-9,]+)\s*円", text)
    if price:
        details["share_price"] = price.group(1).replace(",", "")

    count = re.search(r"発行新株式数[^0-9]*([0-9,]+)\s*株", text)
    if count:
        details["share_count"] = count.group(1).replace(",", "")

    d_match = re.search(
        r"(?:払込期日|割当日|発行日)[^0-9]*([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日", text
    )
    if d_match:
        details["deal_date"] = f"{d_match.group(1)}/{d_match.group(2)}/{d_match.group(3)}"

    if "新株予約権" in text:
        details["deal_structure"] = "Warrant/Stock Option"
    elif "転換社債" in text:
        details["deal_structure"] = "Convertible Bond"
    elif "新株式" in text:
        details["deal_structure"] = "Common Stock"

    return details

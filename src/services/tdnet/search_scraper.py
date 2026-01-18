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
import re
import os
import logging
import requests
from datetime import datetime, date
from typing import List, Optional, Set, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import quote

from .search_models import TdnetSearchEntry, TdnetSearchResult

# Configure logging
logger = logging.getLogger(__name__)

# Try importing pypdf
try:
    from pypdf import PdfReader

    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


class TdnetSearchScraper:
    """
    Scraper for TDnet Search (tdnet-search.appspot.com).
    """

    BASE_URL = "https://tdnet-search.appspot.com/search"

    SEARCH_TERMS = {
        "tier1": [
            {
                "query": "第三者割当 発行に関するお知らせ",
                "precision": "95%+",
                "description": "Initial issuance announcements",
            },
            {
                "query": "第三者割当 募集に関するお知らせ",
                "precision": "95%+",
                "description": "Initial offering announcements",
            },
        ],
        "tier2": [
            {
                "query": "第三者割当 新株式 -払込完了",
                "precision": "90%+",
                "description": "Common stock issuances (excluding completions)",
            },
            {
                "query": "第三者割当 新株予約権 -払込完了",
                "precision": "90%+",
                "description": "Warrant issuances (excluding completions)",
            },
        ],
        "tier3": [
            {
                "query": "第三者割当 割当先決定",
                "precision": "85%+",
                "description": "Allottee decision announcements",
            },
        ],
    }

    TIER_MAPPING = {"tier1": "Tier 1 (95%+)", "tier2": "Tier 2 (90%+)", "tier3": "Tier 3 (85%+)"}

    def __init__(self, delay: float = 1.0, download_pdfs: bool = False, output_dir: str = "."):
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
        """
        all_entries: List[TdnetSearchEntry] = []
        seen_keys: Set[str] = set()
        metadata = {"search_terms_used": []}

        logger.info(f"Starting scrape for range: {start_date} to {end_date}")

        for tier_name, terms in self.SEARCH_TERMS.items():
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

                    results = self._parse_results(html)

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
                            d = self._parse_date_str(r["publish_date"])
                            if d:
                                page_dates.append(d)

                        if page_dates and max(page_dates) < start_date:
                            logger.info(
                                f"Reached data before start date on page {page}. Stopping query."
                            )
                            break

                        for r in results:
                            d = self._parse_date_str(r["publish_date"])
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
                            res_dict["tier"] = self.TIER_MAPPING.get(tier_name, "Unknown")

                            # Create model
                            try:
                                entry = TdnetSearchEntry(**res_dict)

                                # PDF Extraction
                                if self.download_pdfs and entry.pdf_url and HAS_PYPDF:
                                    pdf_text = self._download_and_extract_pdf(
                                        entry.pdf_url, entry.doc_id
                                    )
                                    if pdf_text:
                                        entry.pdf_downloaded = True
                                        details = self._extract_deal_details(pdf_text)
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
        try:
            params = {"query": query, "page": page}
            resp = self.session.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.error(f"Error fetching page {page} for query '{query}': {e}")
            return None

    def _parse_results(self, html: str) -> List[Dict[str, Any]]:
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
                    date_obj = self._parse_date_str(datetime_text.split()[0])
                    if not date_obj:
                        i += 1
                        continue

                    title_link = title_cell.find("a")
                    if title_link:
                        title = title_link.get_text(strip=True)
                        pdf_link = self._extract_pdf_link(row)
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

    def _extract_pdf_link(self, row) -> Optional[str]:
        links = row.find_all("a")
        for link in links:
            href = link.get("href", "")
            if "pdf" in href.lower() or "release.tdnet.info" in href:
                return href
        return None

    def _parse_date_str(self, date_str: str) -> Optional[date]:
        """Parse YYYY/MM/DD or YYYY-MM-DD string to date object"""
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

    def _download_and_extract_pdf(self, url: str, doc_id: str) -> Optional[str]:
        if not HAS_PYPDF:
            return None
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()

            pdf_path = os.path.join(self.output_dir, f"{doc_id}.pdf")
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

    def _extract_deal_details(self, text: str) -> Dict[str, Any]:
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

import csv
import time
import requests
import os
from datetime import datetime, timedelta
from typing import List
from bs4 import BeautifulSoup


class TDnetPDFBackfill:
    """Class for backfilling TDnet PDF links"""

    def __init__(self, input_file: str, output_file: str = None):
        self.input_file = input_file
        self.output_file = output_file or input_file.replace(".csv", "_backfilled.csv")
        self.data = []
        self.stats = {"total": 0, "missing_pdf": 0, "backfilled": 0, "still_missing": 0}

    def load_data(self):
        """Load the CSV data"""
        if not os.path.exists(self.input_file):
            print(f"File not found: {self.input_file}")
            return

        with open(self.input_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.data = list(reader)
        self.stats["total"] = len(self.data)
        self.stats["missing_pdf"] = sum(
            1 for row in self.data if not row.get("pdf_link", "").strip()
        )
        print(
            f"Loaded {self.stats['total']} entries, {self.stats['missing_pdf']} missing PDF links"
        )

    def save_data(self):
        """Save the updated data to CSV"""
        if not self.data:
            return

        fieldnames = self.data[0].keys()
        with open(self.output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.data)
        print(f"Saved {len(self.data)} entries to {self.output_file}")

    def backfill_from_tdnet_official(self, max_days_back: int = 30):
        """
        Backfill PDF links from TDnet official archive.
        Only works for recent data (~30 days).

        URL Pattern: https://www.release.tdnet.info/inbs/I_list_001_{YYYYMMDD}.html
        """
        print("\n" + "=" * 60)
        print("Strategy 1: TDnet Official Archive")
        print("=" * 60)

        # Get unique dates that need backfilling
        dates_to_check = set()
        for row in self.data:
            if not row.get("pdf_link", "").strip():
                date_str = row.get("date", "")
                if date_str:
                    dates_to_check.add(date_str)

        print(f"Dates with missing PDFs: {len(dates_to_check)}")

        # Build a cache of PDF links by date
        pdf_cache = {}  # {date: {(stock_code, title_fragment): pdf_url}}

        for date_str in sorted(dates_to_check, reverse=True):
            date_yyyymmdd = date_str.replace("-", "")
            url = f"https://www.release.tdnet.info/inbs/I_list_001_{date_yyyymmdd}.html"

            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    links = soup.find_all("a", href=True)

                    pdf_cache[date_str] = {}
                    for link in links:
                        href = link.get("href", "")
                        if ".pdf" in href:
                            title = link.text.strip()
                            # Extract stock code from nearby elements if possible
                            pdf_url = (
                                f"https://www.release.tdnet.info/inbs/{href}"
                                if not href.startswith("http")
                                else href
                            )
                            pdf_cache[date_str][title] = pdf_url

                    print(f"  ✓ {date_str}: Found {len(pdf_cache[date_str])} PDFs")
                else:
                    print(f"  ✗ {date_str}: HTTP {response.status_code} (data not available)")

            except Exception as e:
                print(f"  ✗ {date_str}: Error - {e}")

            time.sleep(0.5)  # Rate limiting

        # Match and backfill
        backfilled = 0
        for row in self.data:
            if not row.get("pdf_link", "").strip():
                date_str = row.get("date", "")
                title = row.get("title", "")

                if date_str in pdf_cache:
                    # Try exact title match
                    if title in pdf_cache[date_str]:
                        row["pdf_link"] = pdf_cache[date_str][title]
                        backfilled += 1
                    else:
                        # Try partial match
                        for cached_title, pdf_url in pdf_cache[date_str].items():
                            if title[:30] in cached_title or cached_title[:30] in title:
                                row["pdf_link"] = pdf_url
                                backfilled += 1
                                break

        print(f"\nBackfilled {backfilled} PDF links from TDnet Official")
        self.stats["backfilled"] += backfilled
        return backfilled

    def run(self, strategies: List[str] = None):
        """Run the backfill process with specified strategies"""
        if strategies is None:
            strategies = ["tdnet_official"]

        self.load_data()

        for strategy in strategies:
            if strategy == "tdnet_official":
                self.backfill_from_tdnet_official()

        # Calculate final stats
        self.stats["still_missing"] = sum(
            1 for row in self.data if not row.get("pdf_link", "").strip()
        )

        # Save results
        self.save_data()

        # Print summary
        print("\n" + "=" * 60)
        print("BACKFILL SUMMARY")
        print("=" * 60)
        print(f"Total entries: {self.stats['total']}")
        print(f"Initially missing: {self.stats['missing_pdf']}")
        print(f"Backfilled: {self.stats['backfilled']}")
        print(f"Still missing: {self.stats['still_missing']}")

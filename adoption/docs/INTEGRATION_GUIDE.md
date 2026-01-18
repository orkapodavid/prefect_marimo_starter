# Market Intelligence Modules Integration Guide

This guide details how to incorporate the TDnet and FEFTA market intelligence scraping modules into your repository. These modules provide automated retrieval and processing of financial disclosures and company classification data.

## 1. Module Overview

### TDnet Modules
*   **`tdnet/announcement_scraper.py`**: A bilingual (English/Japanese) scraper for the TDnet Company Announcements Service. It handles date range validation, pagination, and HTML parsing to extract structured announcement metadata including PDF URLs and XBRL availability.
*   **`tdnet/search_scraper.py`**: A specialized scraper for the TDnet Search service (`tdnet-search.appspot.com`), focused on finding specific capital structure changes (e.g., third-party allotments). It supports tiered keyword searching and optional PDF text extraction.

### FEFTA Modules
*   **`fefta/fefta_crawler.py`** (Crawler Service): orchestrates the retrieval of the Ministry of Finance's "Related Guidance and Documents" page, identifies the latest Excel file based on "As of" dates, and downloads it.
*   **`fefta/fefta_crawler.py`** (Data Processor): The processing logic is currently embedded within the crawler. It parses the specific "Listed Companies" sheet, normalizes Japanese circled numerals (e.g., ① → 1) to integers, and maps columns to Pydantic models.

## 2. Dependencies

Ensure your `pyproject.toml` includes the following dependencies. Versions specified are recommended baselines.

```toml
[project]
dependencies = [
    "beautifulsoup4>=4.14.3",
    "httpx>=0.28.1",       # Required for FEFTA and modern async support
    "lxml>=6.0.2",        # High-performance HTML parsing
    "openpyxl>=3.1.5",    # Excel file reading
    "pandas>=2.3.3",      # Data manipulation
    "pydantic>=2.0",      # Data validation and modeling
    "pypdf>=6.6.0",       # PDF text extraction (for search_scraper)
    "requests>=2.32.5",   # Required for TDnet scrapers
]
```

## 3. Installation Instructions

1.  **Copy the Source Code**:
    Copy the `src/tdnet` and `src/fefta` directories into your repository's source tree (e.g., `src/market_intelligence/` or directly under `src/`).

2.  **Set Up Virtual Environment**:
    ```powershell
    # Create virtual environment
    uv venv

    # Activate
    .venv\Scripts\activate

    # Install dependencies
    uv sync
    # OR if using pip manually:
    pip install -r requirements.txt
    ```

## 4. Import Structure

Assuming the modules are placed in `src/`, imports should follow this pattern:

```python
# TDnet
from tdnet.announcement_models import TdnetLanguage, TdnetAnnouncement
from tdnet.announcement_scraper import TdnetAnnouncementScraper, scrape_announcements
from tdnet.search_scraper import TdnetSearchScraper

# FEFTA
from fefta.models import FeftaSource, FeftaRecord
from fefta.fefta_crawler import FeftaCrawler, FeftaCrawlerError
```

## 5. Usage Examples

### TDnet Announcement Scraper

```python
from datetime import date
from tdnet.announcement_scraper import TdnetAnnouncementScraper, TdnetLanguage

# Initialize scraper (English by default)
scraper = TdnetAnnouncementScraper(delay=1.0)

# Scrape a date range
start_date = date(2026, 1, 14)
end_date = date(2026, 1, 15)
result = scraper.scrape(start_date, end_date)

print(f"Found {result.total_count} announcements.")
for ann in result.announcements:
    print(f"{ann.publish_date}: {ann.company_name} - {ann.title}")
    if ann.pdf_url:
        print(f"  PDF: {ann.pdf_url}")

# Scrape Japanese version
jp_scraper = TdnetAnnouncementScraper(language=TdnetLanguage.JAPANESE)
jp_result = jp_scraper.scrape(start_date, end_date)
```

### TDnet Search Scraper

```python
from datetime import date
from tdnet.search_scraper import TdnetSearchScraper

# Initialize with PDF downloading enabled
scraper = TdnetSearchScraper(download_pdfs=True, output_dir="./data/pdfs")

# Run tiered search
result = scraper.scrape(
    start_date=date(2025, 1, 1),
    end_date=date(2025, 1, 31)
)

for entry in result.entries:
    print(f"Tier {entry.tier}: {entry.company_name} - {entry.title}")
    # Access extracted deal details if PDF was parsed
    if entry.deal_size:
        print(f"  Deal Size: {entry.deal_size} {entry.deal_size_currency}")
```

### FEFTA Crawler

```python
from fefta.fefta_crawler import FeftaCrawler

# Initialize crawler (output_dir defaults to data/output/fefta)
with FeftaCrawler() as crawler:
    # 1. Fetch latest source info
    source = crawler.fetch_latest_source()
    print(f"Latest source as of: {source.as_of_date}")
    
    # 2. Download Excel
    source = crawler.download_excel(source)
    print(f"Saved to: {source.saved_path}")
    
    # 3. Parse records
    records, df = crawler.parse_records(source.saved_path)
    
    print(f"Parsed {len(records)} companies.")
    print(df.head())
```

## 6. Configuration Requirements

*   **Environment Variables**: None required by default.
*   **Filesystem**:
    *   FEFTA crawler requires write access to `data/output/fefta` (or configured `output_dir`).
    *   TDnet Search scraper (if PDF download enabled) requires write access to its `output_dir`.
*   **Network**:
    *   Access to `www.release.tdnet.info` (TDnet Announcements).
    *   Access to `tdnet-search.appspot.com` (TDnet Search).
    *   Access to `www.mof.go.jp` (FEFTA).

## 7. File Organization

Recommended directory structure for the target repository:

```text
pyproject.toml
src/
├── fefta/
│   ├── __init__.py
│   ├── fefta_crawler.py  # Contains crawler and processing logic
│   └── models.py
└── tdnet/
    ├── __init__.py
    ├── announcement_helpers.py
    ├── announcement_models.py
    ├── announcement_scraper.py
    ├── search_models.py
    └── search_scraper.py
```

## 8. Error Handling

Wrap scraper calls in try/except blocks to handle specific exceptions:

```python
from tdnet.announcement_scraper import TdnetScraperError, TdnetRequestError
from fefta.fefta_crawler import FeftaCrawlerError, FeftaLinkNotFoundError

try:
    # generic scraping call
    pass
except TdnetRequestError as e:
    # Handle network/HTTP errors specifically
    print(f"Network error: {e}")
except TdnetScraperError as e:
    # Handle parsing or logic errors
    print(f"Scraping failed: {e}")
except FeftaLinkNotFoundError:
    # Specific FEFTA case: no Excel file found on page
    print("No FEFTA file found.")
except FeftaCrawlerError as e:
    print(f"FEFTA Error: {e}")
```

## 9. Testing Integration

### Running Existing Tests
If the source repository includes tests, run them using `pytest`:

```bash
uv run pytest tests/
```

### Writing New Tests
When integrating, verify functionality with "smoke tests" that mock network requests to avoid hitting live servers:

```python
# tests/test_integration.py
import pytest
from tdnet.announcement_models import TdnetAnnouncement

def test_announcement_model_validation():
    """Verify core models work with your data expectations."""
    ann = TdnetAnnouncement(
        publish_datetime="2026-01-01T10:00:00",
        publish_date="2026-01-01",
        stock_code="1234",
        company_name="Test Corp",
        title="Test Announcement",
        language="english"
    )
    assert ann.stock_code == "1234"
```

## 10. Best Practices

1.  **Rate Limiting**: The scrapers have built-in delays (`delay` parameter). **Do not set this to 0.** Respect the target servers.
    *   TDnet: Default 1.0s.
    *   FEFTA: Default 1.0s exponential backoff.
2.  **Date Handling**:
    *   TDnet English search has a 31-day limit per request (handled automatically by `scrape()` splitting).
    *   FEFTA is "snapshots" based on "As of" dates.
3.  **Data Processing**:
    *   The FEFTA logic currently resides in `fefta_crawler.py`. If you need to process Excel files offline without crawling, consider refactoring `FeftaCrawler.parse_records` into a standalone class in `fefta/data_processor.py`.
4.  **Logging**: All modules use Python's standard `logging`. Configure a root logger in your application to capture their output:
    ```python
    import logging
    logging.basicConfig(level=logging.INFO)
    ```

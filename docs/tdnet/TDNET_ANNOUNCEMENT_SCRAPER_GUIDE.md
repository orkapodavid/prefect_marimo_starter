'''
# TDnet Announcement Scraper Technical Guide

## 1. Overview

This document provides a comprehensive guide to the `TdnetAnnouncementScraper`, a Python service designed to scrape, parse, and structure company announcements from both the **English** and **Japanese** versions of the TDnet (Timely Disclosure Network) Company Announcements Service.

The scraper is built to be robust, handling pagination, date range chunking, and network errors, while providing a simple interface for developers to fetch timely disclosure data in both languages.

**Key Features:**
- **Bilingual Support**: Fetch announcements in English or Japanese
- **Date Range Scraping**: Fetch announcements for any date range
- **Automatic Chunking**: Automatically splits date ranges longer than 31 days into smaller, valid requests (English)
- **Day-by-Day Scraping**: Scrapes each day individually for Japanese announcements
- **Pagination Handling**: Iterates through all pages of results for a given query
- **Robust Error Handling**: Implements automatic retries with exponential backoff for network requests
- **Structured Data Output**: Uses Pydantic models for type-safe, validated data
- **Flexible Output**: Easily convert results to a pandas DataFrame or a list of dictionaries

## 2. Architecture

The scraper is organized into a modular structure to promote code clarity, maintainability, and testability.

### File Structure
```
research/
├── src/services/tdnet/
│   ├── __init__.py
│   ├── tdnet_announcement_scraper.py    # Main scraper service class
│   ├── tdnet_announcement_helpers.py    # Helper functions for parsing, validation, etc.
│   └── tdnet_announcement_models.py     # Pydantic data models
├── tests/
│   └── test_tdnet_announcement_scraper.py  # Pytest smoke and unit tests
└── docs/tdnet/
    └── TDNET_ANNOUNCEMENT_SCRAPER_GUIDE.md  # This documentation
```

## 3. How to Use

### Quick Start - English (Default)

```python
from datetime import date, timedelta
from services.tdnet.tdnet_announcement_scraper import TdnetAnnouncementScraper

# 1. Initialize the scraper (English by default)
scraper = TdnetAnnouncementScraper(delay=1.0)

# 2. Define the date range
today = date.today()
yesterday = today - timedelta(days=1)

# 3. Scrape the data
try:
    result = scraper.scrape(start_date=yesterday, end_date=today)

    # 4. Process the results
    print(f"Successfully scraped {len(result)} announcements.")

    # Convert to a pandas DataFrame for analysis
    df = result.to_dataframe()
    print(df.head())

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    scraper.close()
```

### Quick Start - Japanese

```python
from datetime import date
from services.tdnet.tdnet_announcement_scraper import TdnetAnnouncementScraper
from services.tdnet.tdnet_announcement_models import TdnetLanguage

# 1. Initialize the scraper for Japanese
scraper = TdnetAnnouncementScraper(
    language=TdnetLanguage.JAPANESE,
    delay=1.0
)

# 2. Scrape today's Japanese announcements
today = date.today()

try:
    result = scraper.scrape(start_date=today, end_date=today)

    print(f"Found {len(result)} Japanese announcements")
    
    # Access Japanese-specific fields
    for ann in result.announcements[:5]:
        print(f"  {ann.company_name}: {ann.title[:50]}...")
        print(f"    Exchange: {ann.listed_exchange}, XBRL: {ann.xbrl_url is not None}")

    df = result.to_dataframe()
    df.to_csv("jp_announcements.csv", index=False, encoding="utf-8-sig")

finally:
    scraper.close()
```

### The `TdnetAnnouncementScraper` Class

This is the main class for interacting with the service.

`class TdnetAnnouncementScraper(language: TdnetLanguage = TdnetLanguage.ENGLISH, delay: float = 1.0, timeout: int = 30, max_retries: int = 3)`

- **`__init__(...)`**: Initializes the scraper.
  - `language`: Language to scrape (`TdnetLanguage.ENGLISH` or `TdnetLanguage.JAPANESE`)
  - `delay`: Time in seconds to wait between HTTP requests.
  - `timeout`: Timeout for each HTTP request.
  - `max_retries`: Number of times to retry a failed request.

- **`scrape(start_date: date, end_date: date, query: str = "") -> TdnetScrapeResult`**: The main scraping method.
  - For English: Handles date range validation, chunking, and pagination automatically.
  - For Japanese: Scrapes each day individually with pagination.
  - `query` parameter only applies to English scraping.

- **`scrape_page(...) -> List[TdnetAnnouncement]`**: Scrapes a single page of results (English only).

- **`get_total_count(...) -> int`**: Fetches only the total count of announcements for a query without scraping all pages (English only).

- **`close()`**: Closes the underlying `requests.Session`.

## 4. Language Differences

| Aspect | English | Japanese |
|--------|---------|----------|
| **URL** | POST to search endpoint | GET to date-specific URLs |
| **Date Range** | Max 31 days per request | One day per request |
| **Search Query** | Supported | Not supported |
| **Items Per Page** | 200 | ~100 |
| **Special Fields** | `sector` | `listed_exchange`, `xbrl_url` |
| **Encoding** | UTF-8 | UTF-8 |

## 5. Data Models (`tdnet_announcement_models.py`)

Data is structured using Pydantic models for validation and clarity.

### `TdnetLanguage`

Enum for language selection:
- `TdnetLanguage.ENGLISH` - English version
- `TdnetLanguage.JAPANESE` - Japanese version

### `TdnetAnnouncement`

Represents a single announcement record.

| Field              | Type           | Description                                      | Language |
|--------------------|----------------|--------------------------------------------------|----------|
| `publish_datetime` | `datetime`     | Full publication timestamp                       | Both     |
| `publish_date`     | `date`         | Date of publication                              | Both     |
| `stock_code`       | `str`          | Company stock code (e.g., "40620")               | Both     |
| `company_name`     | `str`          | Name of the company                              | Both     |
| `title`            | `str`          | Title of the announcement                        | Both     |
| `pdf_url`          | `Optional[str]`| URL to the full PDF document                     | Both     |
| `has_xbrl`         | `bool`         | True if XBRL data is linked                      | Both     |
| `notes`            | `str`          | Note, e.g., "Summary", "Delayed", "Updated"      | Both     |
| `language`         | `TdnetLanguage`| Language of the announcement                     | Both     |
| `sector`           | `Optional[str]`| Industry sector                                  | EN only  |
| `listed_exchange`  | `Optional[str]`| Exchange abbreviation (東, 名, etc.)              | JP only  |
| `xbrl_url`         | `Optional[str]`| Direct URL to XBRL zip file                      | JP only  |

### `TdnetScrapeResult`

Represents the complete result of a scrape operation.

| Field           | Type                    | Description                                      |
|-----------------|-------------------------|--------------------------------------------------|
| `start_date`    | `date`                  | The start date of the query                      |
| `end_date`      | `date`                  | The end date of the query                        |
| `query`         | `str`                   | The search query string used                     |
| `total_count`   | `int`                   | Total announcements found                        |
| `page_count`    | `int`                   | Number of pages scraped                          |
| `announcements` | `List[TdnetAnnouncement]`| The list of scraped announcement objects        |
| `scraped_at`    | `datetime`              | Timestamp of when the scrape was completed       |
| `language`      | `TdnetLanguage`         | Language of the scrape                           |

This class also provides two helpful methods:
- **`to_dataframe() -> pd.DataFrame`**: Converts the `announcements` list into a pandas DataFrame.
- **`to_list() -> List[dict]`**: Converts the `announcements` list into a list of dictionaries.

## 6. Helper Functions (`tdnet_announcement_helpers.py`)

This module contains utility functions used by the main scraper.

### English Helpers
- **`format_date_param(d: date) -> str`**: Converts a `date` object to the `YYYYMMDD` string format.
- **`parse_datetime_text(text: str) -> Tuple[datetime, date]`**: Parses the date string from the TDnet table.
- **`extract_total_count(html: str) -> int`**: Finds the "Total X Announcements" text in the HTML.
- **`calculate_page_count(total: int) -> int`**: Calculates the number of pages to scrape.
- **`build_request_payload(...) -> Dict`**: Constructs the dictionary for the POST request body.
- **`parse_announcement_row(row: Tag) -> Optional[Dict]`**: Parses a single `<tr>` BeautifulSoup tag.
- **`split_date_range(...) -> List[Tuple[date, date]]`**: Splits a wide date range into smaller chunks.

### Japanese Helpers
- **`build_japanese_url(page: int, target_date: date) -> str`**: Builds URL for Japanese page.
- **`parse_japanese_time_text(time_text: str, publication_date: date) -> datetime`**: Parses HH:MM time format.
- **`parse_japanese_announcement_row(row: Tag, publication_date: date) -> Optional[Dict]`**: Parses Japanese table row.
- **`parse_japanese_announcements_from_html(html: str, publication_date: date) -> List[Dict]`**: Parses all Japanese announcements.
- **`get_japanese_request_headers() -> Dict[str, str]`**: Gets headers for Japanese requests.

## 7. Testing

The `test_tdnet_announcement_scraper.py` file contains a suite of `pytest` tests.

- **Unit Tests**: The `TestHelperFunctions`, `TestModels`, and `TestJapaneseHelperFunctions` classes test individual functions and Pydantic models in isolation.
- **Integration/Smoke Tests**: The `TestScraperIntegration` and `TestJapaneseScraperIntegration` classes run tests that make live network requests to TDnet.

To run the tests:
```bash
# Install pytest if you haven't already
# pip install pytest

# Run all tests
uv run pytest tests/smoke/tdnet/test_announcement_smoke.py -v

# Run only Japanese tests
uv run pytest tests/smoke/tdnet/test_announcement_smoke.py -v -k "Japanese"
```

This ensures the scraper is functioning as expected for both English and Japanese TDnet.
'''

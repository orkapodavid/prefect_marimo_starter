# FEFTA Crawler Technical Guide

## 1. Overview

This document provides a comprehensive guide to the `FeftaCrawler`, a Python service designed to automate the retrieval and processing of company classification data related to the Foreign Exchange and Foreign Trade Act (FEFTA) from the Japanese Ministry of Finance (MOF).

**Key Features:**
- **Automated Discovery**: Scrapes the MOF website to find the latest "Listed Companies" Excel file.
- **"As Of" Date Parsing**: Extracts the effective date from the file link to ensure data freshness.
- **Data Normalization**: Handles Japanese circled numerals (e.g., ① → 1) and full-width characters.
- **Structured Data**: Outputs validated Pydantic models for type safety.
- **Robustness**: Includes retries, timeouts, and error handling for network requests.

## 2. Architecture

### File Structure

```
src/services/fefta/
├── __init__.py             # Public exports
├── fefta_constants.py      # Configuration constants
├── fefta_models.py         # Pydantic models + exceptions
├── fefta_helpers.py        # Pure helper functions (date parsing, numeral normalization)
├── fefta_excel_parser.py   # Excel parsing logic
└── fefta_crawler.py        # Main crawler orchestration + HTTP
```

### Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `fefta_crawler.py` | HTTP fetching, orchestration, context management |
| `fefta_helpers.py` | Date parsing, link finding, circled numeral normalization |
| `fefta_excel_parser.py` | Excel file reading, row parsing, column mapping |
| `fefta_models.py` | Pydantic models (`FeftaSource`, `FeftaRecord`) and exceptions |
| `fefta_constants.py` | URLs, User-Agent, month maps, column mappings |

## 3. How to Use

### Basic Usage

The `FeftaCrawler` is designed to be used as a context manager or a standalone instance.

```python
from src.services.fefta import FeftaCrawler

# Initialize crawler (output_dir defaults to data/output/fefta)
with FeftaCrawler() as crawler:
    # 1. Fetch latest source info
    source = crawler.fetch_latest_source()
    print(f"Latest source as of: {source.as_of_date}")
    print(f"File URL: {source.file_url}")
    
    # 2. Download Excel
    source = crawler.download_excel(source)
    print(f"Saved to: {source.saved_path}")
    
    # 3. Parse records
    records, df = crawler.parse_records(source.saved_path)
    
    print(f"Parsed {len(records)} companies.")
    if records:
        print(f"First record: {records[0]}")
```

### Using Helper Functions Directly

For unit testing or custom integrations, you can use helper functions directly:

```python
from src.services.fefta.fefta_helpers import (
    parse_as_of_date,
    normalize_circled_numeral,
    find_fefta_links,
)

# Parse a date from link text
as_of_raw, as_of_date = parse_as_of_date("FEFTA (As of 15 July, 2025)")
print(as_of_date)  # date(2025, 7, 15)

# Convert circled numeral to int
category = normalize_circled_numeral("①", row_idx=0, column_name="category")
print(category)  # 1
```

### Configuration

You can customize the output directory and base URL:

```python
crawler = FeftaCrawler(
    base_url="https://www.mof.go.jp/english/policy/international_policy/fdi/Related_Guidance_and_Documents/index.html",
    output_dir="./custom_data_dir",
    timeout=30,          # HTTP timeout in seconds
    max_retries=5,       # Retry attempts for failed requests
    retry_delay=2.0,     # Base delay between retries
)
```

## 4. Data Models (`fefta_models.py`)

### `FeftaSource`

Tracks the source file information.

| Field | Type | Description |
|-------|------|-------------|
| `as_of_raw` | `str` | Raw "As of" text from the website link. |
| `as_of_date` | `date` | Parsed ISO date from `as_of_raw`. |
| `download_date` | `date` | Date the file was downloaded (today). |
| `file_url` | `str` | Absolute URL to the Excel file. |
| `saved_path` | `Optional[str]` | Local path to the downloaded file. |

### `FeftaRecord`

Represents a single row from the Excel file.

| Field | Type | Description | Original Column |
|-------|------|-------------|-----------------|
| `securities_code` | `str` | Stock code (e.g., "7203") | `証券コード (Securities code)` |
| `isin_code` | `str` | ISIN code | `ISINコード (ISIN code)` |
| `company_name_ja` | `str` | Japanese company name | `会社名（和名）` |
| `issue_or_company_name` | `str` | English company/issue name | `(Issue name / company name)` |
| `category` | `int` | FEFTA Category (1-10) | `区分` |
| `core_operator` | `Optional[int]` | Core Operator flag (1-10) | `特定コア事業者` |

**Note**: `category` and `core_operator` are parsed from Japanese circled numerals (e.g., ① becomes 1).

## 5. Error Handling

The module emits specific exceptions defined in `fefta_models.py`:

| Exception | Description |
|-----------|-------------|
| `FeftaCrawlerError` | Base exception for all crawler errors |
| `FeftaLinkNotFoundError` | Excel file link cannot be found on the page |
| `FeftaDateParseError` | "As of" date cannot be parsed from link text |
| `FeftaExcelParseError` | Excel file structure is invalid or parsing fails |

Example:

```python
from src.services.fefta import (
    FeftaCrawler,
    FeftaLinkNotFoundError,
    FeftaExcelParseError,
)

try:
    with FeftaCrawler() as crawler:
        source, records = crawler.run()
except FeftaLinkNotFoundError:
    print("Could not find the Excel file on the MOF page.")
except FeftaExcelParseError as e:
    print(f"Failed to parse the Excel file: {e}")
```

## 6. Testing

### Test Structure

```
tests/
├── unit/fefta/
│   ├── test_fefta_helpers.py    # Unit tests for helper functions (no network)
│   └── test_fefta_crawler.py    # Integration tests (live HTTP)
└── smoke/fefta/
    └── test_fefta_smoke.py      # End-to-end smoke tests
```

### Running Tests

```bash
# Run unit tests for helpers (fast, no network)
uv run pytest tests/unit/fefta/test_fefta_helpers.py -v

# Run smoke tests (live HTTP requests)
uv run pytest tests/smoke/fefta/ -v -s

# Run all FEFTA tests
uv run pytest tests/unit/fefta/ tests/smoke/fefta/ -v
```

### Test Coverage

| Test File | Test Count | Coverage |
|-----------|------------|----------|
| `test_fefta_helpers.py` | 35 | Date parsing, link finding, numeral normalization, column mapping |
| `test_fefta_smoke.py` | 3 | Live fetch, download, parse workflow |

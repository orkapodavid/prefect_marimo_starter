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
├── __init__.py
├── fefta_crawler.py  # Main crawler and processing logic
└── models.py         # Pydantic data models (FeftaSource, FeftaRecord)
```

## 3. How to Use

### Basic Usage

The `FeftaCrawler` is designed to be used as a context manager or a standalone instance.

```python
from services.fefta.fefta_crawler import FeftaCrawler

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

### Configuration

You can customize the output directory and base URL:

```python
crawler = FeftaCrawler(
    base_url="https://www.mof.go.jp/english/policy/international_policy/fdi/Related_Guidance_and_Documents/index.html",
    output_dir="./custom_data_dir"
)
```

## 4. Data Models (`models.py`)

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

The module emits specific exceptions in `fefta_crawler.py`:

- `FeftaCrawlerError`: Base exception for all crawler errors.
- `FeftaLinkNotFoundError`: Raised when the Excel file link cannot be found on the page.
- `FeftaExcelParseError`: Raised when the Excel file structure is invalid or parsing fails.

Example:

```python
try:
    crawler.run()
except FeftaLinkNotFoundError:
    print("Could not find the Excel file on the MOF page.")
except FeftaExcelParseError as e:
    print(f"Failed to parse the Excel file: {e}")
```

## 6. Testing

Tests are located in `tests/smoke/fefta/`.

To run tests:

```bash
uv run pytest tests/smoke/fefta/
```

This verifies:
1.  **Network**: Can connect to MOF website (mocked or live).
2.  **Parsing**: Can correctly identify links and parse "As of" dates.
3.  **Excel**: Can download and extract data from the file.

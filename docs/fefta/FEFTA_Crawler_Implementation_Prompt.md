# FEFTA Crawler Implementation Prompt (Python)

## Goal
Implement an importable Python helper service that:
- Browses MOF’s “Related Guidance and Documents” page
  - URL: https://www.mof.go.jp/english/policy/international_policy/fdi/Related_Guidance_and_Documents/index.html
- Finds the latest FEFTA Excel link (anchor containing “FEFTA”, href ending with `.xlsx`), captures the link text and URL
- Parses the “As of …” date from the link text, storing both the raw text and the parsed ISO date
- Downloads the Excel file and saves it to `data/output/fefta/` with a filename prefix of today’s date in `YYYY_MM_DD` format followed by the original filename (keep extension)
- Reads the sheet named `上場企業の該当性リスト` and maps the circled numerals to integers
- Validates and returns structured data via Pydantic v2 models (English field names; Japanese values preserved)

Libraries to use: `httpx`, `BeautifulSoup` (bs4), `pandas`, `pydantic v2`.

## Scope & Constraints
- Class must be import-safe (no side effects on import). Provide an orchestrating `run()` method callable by other functions
- English field names in Pydantic models; allow Japanese data (UTF-8)
- Use robust HTTP settings (timeouts, retries/backoff, user-agent)
- Graceful error handling with informative exceptions and optional logging

## Data Models (Pydantic v2)
Define two models with English field names; Japanese values allowed where applicable.

```python
from datetime import date
from pydantic import BaseModel
from typing import Optional

class FeftaSource(BaseModel):
    as_of_raw: str             # e.g., "As of 15 July, 2025"
    as_of_date: date           # parsed from as_of_raw (ISO YYYY-MM-DD)
    download_date: date        # today’s date (ISO YYYY-MM-DD)
    file_url: str              # absolute Excel URL discovered
    saved_path: Optional[str]  # absolute path where Excel is saved

class FeftaRecord(BaseModel):
    securities_code: str           # 証券コード (Securities code)
    isin_code: str                 # ISINコード (ISIN code)
    company_name_ja: str           # 会社名（和名）
    issue_or_company_name: str     # (Issue name / company name)
    category: int                  # 区分 (①→1, ②→2, …, ⑩→10)
    core_operator: int             # 特定コア事業者 (①→1, ②→2, …, ⑩→10)
```

Validation requirements:
- All fields required unless `Optional` shown
- `securities_code`, `isin_code` must preserve leading zeros; read as strings
- Circled numerals must map to integers (1–10). If non-mapped value encountered, raise a validation error with the offending row index

## Locating the FEFTA Excel Link
- Fetch the MOF page with `httpx`
- Parse with `BeautifulSoup`
- Strategy:
  - Find anchor tags `<a>` whose text contains “FEFTA” and whose `href` ends with `.xlsx`
  - Extract both the `href` and the full visible link text (which includes the "As of …")
  - If multiple anchors match, choose the one with the latest parsed "As of" date by comparing dates
- Ensure absolute URL handling (join relative hrefs with the page’s base)

Example of expected link (subject to change):
- Link text: `the "List of classifications of listed companies regarding the prior-notification requirements on inward direct investment under the FEFTA"（As of 15 July, 2025）(Excel:296KB)`
- Href: `https://www.mof.go.jp/english/policy/international_policy/fdi/Related_Guidance_and_Documents/gaitouseilist20250715.xlsx`

## Parsing the “As of” Date
- Use a regex pattern to extract day, month name, year from the link text:
  - Pattern: `As of (\d{1,2}) ([A-Za-z]+), (\d{4})`
- Month-name map: `{"January":1, "February":2, "March":3, "April":4, "May":5, "June":6, "July":7, "August":8, "September":9, "October":10, "November":11, "December":12}`
- Convert to ISO date (`YYYY-MM-DD`)
- Store both `as_of_raw` and parsed `as_of_date`
- Also store `download_date` (today’s date in ISO)
- If parsing fails, raise a descriptive error containing the link text

## HTTP Fetching & File Saving
- Use `httpx.Client` with:
  - Timeouts (connect/read): e.g., 10–20s
  - Retries/backoff: use a simple loop and `try/except` for idempotent GET
  - Custom `User-Agent` header
  - SSL verification enabled
- Download path: `data/output/fefta/`
- Filename convention: `YYYY_MM_DD` prefix + original filename (keep extension). For example: `2026_01_17_gaitouseilist20250715.xlsx`
- Ensure directories exist before writing
- Return absolute `saved_path` in `FeftaSource`

## Excel Parsing Requirements
- Sheet name: `上場企業の該当性リスト`
- Use `pandas.read_excel` with engine auto-detection (`openpyxl` recommended)
- Encoding: Japanese characters must be preserved (pandas+openpyxl will handle)
- Dtypes: Read `securities_code` and `isin_code` as strings (`dtype=str`) to preserve leading zeros
- Expected columns (in this order):
  1. `証券コード (Securities code)` → `securities_code`
  2. `ISINコード (ISIN code)` → `isin_code`
  3. `会社名（和名）` → `company_name_ja`
  4. `(Issue name / company name)` → `issue_or_company_name`
  5. `区分` → `category` (circled numeral → int)
  6. `特定コア事業者` → `core_operator` (circled numeral → int)
- If the columns differ, implement a robust mapping by matching substrings or exact labels; raise an error if any required column is missing

## Circled Numerals Normalization
- Map circled numerals to integers:
  - `①→1`, `②→2`, `③→3`, `④→4`, `⑤→5`, `⑥→6`, `⑦→7`, `⑧→8`, `⑨→9`, `⑩→10`
- Normalize:
  - Strip surrounding whitespace
  - Handle full-width/half-width variants if present
  - Accept either circled characters or plain digits; plain digits should be int-castable
- Error handling:
  - If value is unmapped or empty, raise a validation error with row index and column name

## Helper Class Design & Public API
Create an importable helper class, e.g., `FeftaCrawler`, with methods:

```python
from typing import List, Tuple
import pandas as pd

class FeftaCrawler:
    def __init__(self, base_url: str = "https://www.mof.go.jp/english/policy/international_policy/fdi/Related_Guidance_and_Documents/index.html"):
        """Configure client defaults, headers, timeouts, etc."""

    def fetch_latest_source(self) -> FeftaSource:
        """Fetch page, locate FEFTA Excel link(s), choose the latest by parsed as_of date.
        Returns FeftaSource without saved_path set yet."""

    def download_excel(self, source: FeftaSource) -> FeftaSource:
        """Download the Excel from source.file_url, save to data/output/fefta/
        with YYYY_MM_DD prefix, set and return source.saved_path."""

    def parse_records(self, saved_path: str) -> Tuple[List[FeftaRecord], pd.DataFrame]:
        """Read sheet 上場企業の該当性リスト, map columns to models, normalize circled numerals.
        Return list of FeftaRecord and the raw DataFrame for optional further use."""

    def run(self) -> Tuple[FeftaSource, List[FeftaRecord]]:
        """End-to-end orchestration: fetch_latest_source → download_excel → parse_records."""
```

Notes:
- No side effects on import; all work behind methods
- Provide minimal logging (info/warn) where helpful

## Error Handling & Testing
Handle and raise informative exceptions for:
- Network errors (timeouts, connection issues)
- No matching FEFTA anchors or `.xlsx` links found
- Date parse failures on link text
- Missing sheet `上場企業の該当性リスト`
- Missing/renamed columns
- Invalid circled numerals

Testing checklist:
- Can discover the FEFTA Excel link on the MOF page
- Correctly parses `as_of_raw` and `as_of_date` from link text
- Saves Excel with `YYYY_MM_DD` prefix + original filename under `data/output/fefta/`
- Reads the specified sheet and maps columns as defined
- Converts circled numerals to integers
- Returns valid `FeftaSource` and a non-empty list of `FeftaRecord`

## Acceptance Criteria
- Latest FEFTA Excel link discovered; URL and link text captured
- `as_of_raw`, `as_of_date` (ISO), and `download_date` populated in `FeftaSource`
- Excel saved to `data/output/fefta/` with correct filename convention; `saved_path` set
- Sheet `上場企業の該当性リスト` parsed; columns mapped correctly
- Circled numerals normalized to `int`
- Pydantic v2 validation passes for all records
- Class is importable and callable by other functions without modification

## Implementation Tips
- Use `httpx.Client` for session-level headers/timeouts
- Prefer `urljoin` from `urllib.parse` for absolute URL resolution
- For date parsing, lower-case the month name before mapping, and accept common abbreviations (`Jan`, `Feb`, …) as a fallback if they appear
- Use `dtype=str` for `read_excel` to keep codes intact; then cast numeric fields after normalization
- Consider `try/except` with a small retry loop (e.g., up to 3 attempts) for network calls

# TDnet Search Scraper Technical Guide

## Overview
This guide covers the technical implementation, architecture, and maintenance of the TDnet Search Scraper suite (`src/services/tdnet/tdnet_search_*.py`). This suite provides targeted scraping for "Third-Party Allotment" announcements, data analysis, and PDF backfilling capabilities.

## 1. System Architecture

The project uses a modular architecture with specialized components in `src/services/tdnet/`:

### File Organization

```
src/services/tdnet/
├── __init__.py                   # Package exports
├── tdnet_exceptions.py           # Exception hierarchy (TdnetScraperError, etc.)
├── tdnet_search_scraper.py       # Core scraping engine
├── tdnet_search_constants.py     # Search terms and tier definitions
├── tdnet_search_helpers.py       # Parsing and extraction functions
├── tdnet_search_models.py        # Pydantic models (TdnetSearchEntry, etc.)
├── tdnet_search_analysis.py      # Analysis and reporting
└── tdnet_search_backfill.py      # PDF backfill utilities
```

### A. TdnetSearchScraper (`tdnet_search_scraper.py`)
*   **Purpose**: Core scraping engine for third-party allotment announcements.
*   **Data Source**: TDnet Search (https://tdnet-search.appspot.com)
*   **Key Features**:
    *   **Tiered Search**: Uses precision-targeted queries (Tier 1-3).
    *   **Date Filtering**: Client-side filtering and optimization (stops early if data is too old).
    *   **PDF Extraction**: Optional download and OCR/text extraction using `pypdf`.
    *   **Deal Details**: Regex-based extraction of investor, deal size, and share details.
*   **Usage**:
    ```python
    from src.services.tdnet import TdnetSearchScraper
    
    scraper = TdnetSearchScraper(download_pdfs=True)
    result = scraper.scrape(start_date=..., end_date=...)
    ```

### B. Search Constants (`tdnet_search_constants.py`)
*   **Purpose**: Centralized configuration for search terms and tier mappings.
*   **Contents**:
    *   `BASE_URL` - TDnet Search endpoint
    *   `SEARCH_TERMS` - Tiered query definitions
    *   `TIER_MAPPING` - Human-readable tier labels

### C. Search Helpers (`tdnet_search_helpers.py`)
*   **Purpose**: Reusable parsing and extraction functions.
*   **Functions**:
    *   `parse_search_results(html)` - Parse HTML table into result dictionaries
    *   `extract_pdf_link(row)` - Extract PDF URL from table row
    *   `parse_date_str(date_str)` - Parse date strings
    *   `download_and_extract_pdf(...)` - Download PDF and extract text
    *   `extract_deal_details(text)` - Extract deal info using regex

### D. TDnetAnalyzer (`tdnet_search_analysis.py`)
*   **Purpose**: Analysis and reporting on scraped datasets.
*   **Capabilities**:
    *   **Company Activity**: Ranks top issuers.
    *   **Temporal Trends**: Daily announcement counts.
    *   **Stock Code Distribution**: Map codes to companies and frequency.
    *   **Announcement Types**: Categorizes deals (Warrants, Convertible Bonds, Common Stock).
    *   **Portfolio Insights**: High-level summary stats.
*   **Usage**:
    ```python
    results = TDnetAnalyzer.load_results('data.json')
    TDnetAnalyzer.analyze_by_company(results)
    ```

### E. TDnetPDFBackfill (`tdnet_search_backfill.py`)
*   **Purpose**: Recover missing PDF links for existing metadata entries.
*   **Strategy**:
    *   **TDnet Official Archive**: Scrapes daily lists from `release.tdnet.info` to find matching PDFs (works for recent ~30 days).
    *   *Planned*: JPX API / EDINET integration.
*   **Usage**:
    ```python
    backfiller = TDnetPDFBackfill('results.csv')
    backfiller.run(strategies=['tdnet_official'])
    ```

## 2. dependencies

*   **Core**: `requests`, `beautifulsoup4`
*   **PDF**: `pypdf` (Optional, but recommended for full detail extraction)
*   **Data**: `pandas` (if used for further processing, though internal logic uses dicts/lists)
*   **Standard**: `csv`, `json`, `re`, `datetime`, `collections`

## 3. Search Strategy (Tiers)

The scraper uses a tiered text search to balance precision and recall. See `TDNET_SEARCH_OPTIMIZATION.md` for full query details.

| Tier | Focus | Key Query Patterns |
|------|-------|-------------------|
| **1** | **Initial Issuance** | `第三者割当` + `発行/募集` (High Precision) |
| **2** | **Stock/Warrants** | `第三者割当` + `新株式/新株予約権` - `払込完了` |
| **3** | **Decisions** | `第三者割当` + `割当先決定` |

## 4. Helper Logic & Details

All helper functions are now in `tdnet_search_helpers.py` for better reusability and testability.

### PDF Link Extraction (`extract_pdf_link`)
The helper looks for `<a>` tags containing `.pdf` or `release.tdnet.info` in the `href`. It extracts the `doc_id` from the URL for uniqueness.

### Deal Text Extraction (`extract_deal_details`)
When PDFs are downloaded, the helper attempts to find:
*   **Investor** (`割当先`)
*   **Amount** (`調達資金`)
*   **Share Price** (`発行価額`)
*   **Share Count** (`発行新株式数`)
*   **Deal Date** (`払込期日` etc.)

### HTML Parsing (`parse_search_results`)
Parses the search results table HTML into a list of dictionaries, handling multi-row entries and description extraction.

### Checkpointing
The scraper writes results incrementally but does not have a formal "resume" file like the simpler version. It relies on the user to manage date ranges or append to existing datasets.

## 5. Maintenance & Troubleshooting

### Common Issues
1.  **"No results found"**: TDnet Search might be blocking IPs or the HTML structure changed. Check `soup.find('table')`.
2.  **PDF Extraction Fails**: Ensure `pypdf` is installed. Some PDFs are image-only (scans) and cannot be parsed without OCR (not currently implemented).
3.  **Backfill Limitations**: The "TDnet Official Archive" strategy only works for the last ~30 days. Older definitions require manual research or paid APIs.

### Adding New Search Terms
Update the `SEARCH_TERMS` dictionary in `src/services/tdnet/tdnet_search_constants.py`. Ensure you assign a new Tier key if needed and update `TIER_MAPPING` with a human-readable label.

# TDnet Third-Party Allotment Scraper Project

## Overview
This project provides a comprehensive tool suite for scraping, analyzing, and archiving "Third-Party Allotment" (第三者割当) announcements from TDnet (Timely Disclosure Network) in Japan. It helps investors and analysts track equity financing events efficiently.

## Documentation Structure

The documentation has been consolidated into three core guides:

1.  **[Search Optimization Guide](docs/SEARCH_OPTIMIZATION.md)**
    *   Best search terms, operators, and negative keywords to ensure 95%+ precision.
    *   Explains how to filter out "Exercise of Rights" and "Corrections".

2.  **[Data Backfill & Strategy](docs/DATA_BACKFILL_STRATEGY.md)**
    *   Solutions for the 30-day PDF retention limit.
    *   Details on using JPX Official API and EDINET API for historical data.

3.  **[Technical Scraper Guide](docs/SCRAPER_TECHNICAL_GUIDE.md)**
    *   Implementation details for `tdnet_scraper_v2.py` and `enhanced`.
    *   HTML structure analysis (handling the `div` vs `ul` parsing issues).

## Quick Start

### 1. Setup
```bash
# Install dependencies
uv sync

# Run tests
uv run pytest
```

### 2. Run Basic Search
```bash
uv run tdnet_scraper.py --period today
```

### 3. Run Enhanced Analysis (with PDF download)
```bash
uv run tdnet_scraper.py --period today --extract-pdfs
```

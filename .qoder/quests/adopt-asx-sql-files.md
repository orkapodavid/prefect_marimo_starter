# Adopt ASX SQL Files and Scripts into Prefect + Marimo Architecture

## Design Objective

Integrate the existing ASX scraper toolset (PIPE announcements, general announcements, Appendix 5B cash flow reports) into the unified Prefect + Marimo notebook architecture. This adoption will transform standalone Python scripts into production-ready Prefect flows with interactive development capabilities.

## Background

The project contains a mature ASX scraping toolset in the `asx/` folder with three primary scrapers:

1. **PIPE Scraper**: Scans all ASX companies for placement/capital raising announcements
2. **General Announcement Scraper**: Fetches announcements for specific tickers over various periods
3. **Appendix 5B Scraper**: Extracts quarterly cash flow reports with Section 8 financial data

Current implementation uses:
- `asx_unified_scraper.py`: Core logic for PIPE and general announcements
- `asx_scraper_classes.py`: Core logic for Appendix 5B with Pydantic models
- Three runner scripts: `asx_pipe_runner.py`, `asx_announcement_runner.py`, `asx_appendix5b_runner.py`
- SQL schema and CRUD operations in `asx/sql/`

## Design Goals

1. **Unified Service Layer**: Merge scraper logic into a single, cohesive `AsxScraperService` following project patterns
2. **Production-Ready Flows**: Convert runners into Marimo notebooks that function as Prefect flows
3. **Database Integration**: Utilize existing SQL files for data persistence via database service
4. **Testability**: Provide comprehensive unit tests with proper mocking
5. **Feature Preservation**: Maintain all existing capabilities (PDF download, parsing, filtering, etc.)

---

## Architecture Design

### 1. Service Layer Consolidation

#### 1.1 AsxScraperService Structure

Create `src/services/asx_scraper/asx_scraper_service.py` to unify scraping capabilities.

**Responsibility Separation:**

| Module | Purpose | Key Responsibilities |
|--------|---------|---------------------|
| `asx_scraper_service.py` | Main service orchestrator | Session management, high-level scraping workflows, database persistence coordination |
| `http_client.py` | HTTP communication | Request handling, retry logic, terms acceptance, session configuration |
| `html_parser.py` | HTML parsing | BeautifulSoup operations, announcement extraction, company list parsing |
| `pdf_handler.py` | PDF operations | Download, text extraction (PyMuPDF + pdfplumber), Section 8 data extraction |
| `models.py` | Data models | Pydantic models for announcements, companies, Section 8 data, scrape results |
| `filters.py` | Business logic filters | PIPE keyword matching, date filtering, announcement classification |

**Design Rationale:**
- Small, focused files following Single Responsibility Principle
- Each module under 300 lines for maintainability
- Clear separation between I/O (http_client), parsing (html_parser), business logic (filters), and orchestration (service)
- Testable components with minimal dependencies

#### 1.2 AsxScraperService API

```
Class: AsxScraperService
├── Initialization
│   ├── Parameters: output_dir, delay, database_service (optional)
│   ├── Creates: http_client, html_parser, pdf_handler instances
│   └── Establishes: output directory structure (pdfs/, json/, csv/)
│
├── Company Operations
│   ├── get_listed_companies() -> List[Company]
│   │   └── Fetches ASX company list, returns structured Company models
│   └── Purpose: Reusable company data source for scan operations
│
├── Announcement Operations
│   ├── get_announcements(ticker, period) -> List[Announcement]
│   │   └── Fetch announcements for specific ticker and time period
│   ├── parse_announcements(html_content, ticker) -> List[Announcement]
│   │   └── Extract structured data from HTML response
│   └── Purpose: Core announcement retrieval and parsing
│
├── PDF Operations
│   ├── download_pdf(url, folder, filename) -> Optional[Path]
│   │   └── Handle ASX terms agreement, download, verify PDF content
│   ├── extract_text_from_pdf(pdf_path) -> str
│   │   └── Dual-strategy extraction (PyMuPDF primary, pdfplumber fallback)
│   └── extract_section8_data(text, pdf_path) -> Section8Data
│       └── Parse Section 8 financial data (items 8.6, 8.7) using text and table extraction
│
├── High-Level Workflows
│   ├── scrape_target_announcements(tickers, period, download_pdfs, save_to_db) -> DataFrame
│   │   ├── Input: List of tickers, time period, download flag, database persistence flag
│   │   ├── Process: Fetch announcements, optionally download PDFs, persist if db available
│   │   └── Output: Pandas DataFrame with announcement metadata
│   │
│   ├── scrape_pipe_announcements(period, download_pdfs, save_to_db, sample_size) -> DataFrame
│   │   ├── Input: Time period, download flag, persistence flag, optional sampling
│   │   ├── Process: Scan all companies, filter by PIPE keywords, download, persist
│   │   └── Output: DataFrame with PIPE-specific announcements
│   │
│   └── scrape_appendix5b_reports(download_pdfs, save_to_db) -> ScrapeSummary
│       ├── Input: Download flag, persistence flag
│       ├── Process: Fetch today's announcements, filter keywords, extract Section 8 data
│       └── Output: Structured ScrapeSummary with extraction success metrics
│
└── Database Integration
    ├── save_announcement(announcement_data, table_type) -> bool
    │   └── Use database service with SQL files from asx/sql/
    ├── Table Types: 'announcement', 'pipe', 'appendix5b'
    └── SQL Mapping: create_*.sql, update_*.sql, read_*.sql
```

**Service Initialization Pattern:**

```
AsxScraperService Configuration:
├── output_dir: Base directory for all outputs (default: 'outputs')
├── delay: Request throttle in seconds (default: 0.5)
├── database_service: Optional database abstraction
│   ├── Expected Interface: execute_query_from_file(file_path, params)
│   ├── Database Type: PostgreSQL (schema.sql compatible)
│   └── SQL File Location: asx/sql/
└── Session Configuration
    ├── Retry Strategy: 3 attempts, exponential backoff
    ├── Timeout: 30 seconds per request
    └── User-Agent: Browser-mimicking headers
```

#### 1.3 Database Service Integration

The `AsxScraperService` will accept an optional `database_service` parameter compatible with the existing `MSSQLService` interface pattern.

**Database Service Contract:**

```
Required Methods:
├── execute_query_from_file(file_path: str, params: dict = None) -> DataFrame
│   └── Execute SQL from file with named or positional parameters
└── execute_query(sql: str, params: dict = None) -> DataFrame
    └── Execute raw SQL with parameters
```

**SQL File Usage Pattern:**

```
Operation Mapping:
├── Create/Insert Announcement
│   ├── File: asx/sql/create_announcement.sql
│   ├── Parameters: ticker, announcement_date, announcement_time, is_price_sensitive, 
│   │              headline, number_of_pages, file_size, pdf_url, downloaded_file_path
│   └── Conflict Handling: ON CONFLICT DO NOTHING (idempotent)
│
├── Create/Insert PIPE Announcement
│   ├── File: asx/sql/create_pipe_announcement.sql
│   ├── Parameters: ticker, company_name, announcement_datetime, title, pdf_link,
│   │              description, is_price_sensitive, downloaded_file_path
│   └── Conflict Handling: ON CONFLICT DO NOTHING
│
├── Create/Insert Appendix 5B Report
│   ├── File: asx/sql/create_appendix_5b_report.sql
│   ├── Parameters: ticker, report_date, headline, pdf_link, total_available_funding,
│   │              estimated_quarters_funding, matched_keywords, extraction_warnings,
│   │              downloaded_file_path
│   └── Conflict Handling: ON CONFLICT DO NOTHING
│
└── Read Operations (Optional for data validation/retrieval)
    ├── read_announcement.sql: Fetch announcements by ticker/date range
    ├── read_pipe_announcement.sql: Fetch PIPE records by ticker/date
    └── read_appendix_5b_report.sql: Fetch cash flow reports by ticker/date
```

**Parameter Adaptation Strategy:**

The service will convert Pydantic models to SQL parameter dictionaries:

```
Model to SQL Parameter Conversion:
├── Announcement Model → create_announcement.sql params
│   └── Map: datetime field → announcement_date + announcement_time split
│
├── PIPE Announcement Model → create_pipe_announcement.sql params
│   └── Map: matched_keywords list → comma-separated string or JSON
│
└── Appendix5B Result Model → create_appendix_5b_report.sql params
    └── Map: Section8Data nested model → flattened parameters
```

**Database Service Abstraction Rationale:**

- Dependency injection pattern allows flexible database backends
- Currently supports PostgreSQL schema (schema.sql)
- Future compatibility: Can adapt to MSSQL, SQLite with service swap
- Testing: Easy to mock database_service in unit tests
- Graceful degradation: Service works without database (file output only)

---

### 2. Marimo + Prefect Notebook Design

Create three notebooks under `notebooks/asx/`:

#### 2.1 Notebook: asx_pipe_scraper.py

**Purpose:** Scan all ASX companies for PIPE/placement announcements and persist results.

**Structure:**

```
Notebook Structure:
│
├── PEP 723 Dependencies Block
│   ├── marimo, prefect, pandas, beautifulsoup4, pymupdf, pdfplumber
│   └── requests, pydantic
│
├── app.setup Block (Shared Imports)
│   ├── from prefect import task, flow
│   ├── from services.asx_scraper import AsxScraperService
│   ├── from services.mssql import MSSQLService (optional)
│   └── import pandas, os, datetime
│
├── @app.function + @task: initialize_services
│   ├── Input: output_dir, use_database (bool)
│   ├── Output: AsxScraperService instance
│   └── Purpose: Initialize scraper with optional database connection
│
├── @app.function + @task: scrape_pipe_announcements
│   ├── Input: service, period, sample_size, download_pdfs
│   ├── Output: DataFrame with PIPE announcements
│   ├── Logic: Call service.scrape_pipe_announcements()
│   └── Logging: Record progress, matched keywords, warnings
│
├── @app.function + @task: persist_results
│   ├── Input: service, dataframe, output_format
│   ├── Output: List of saved file paths
│   ├── Logic: Save CSV, optionally persist to database if service has db
│   └── Purpose: Ensure results are written to disk and database
│
├── @app.function + @flow: run_pipe_scraper
│   ├── Parameters: output_dir, period, sample_size, download_pdfs, use_database
│   ├── Orchestration:
│   │   ├── service = initialize_services(output_dir, use_database)
│   │   ├── df = scrape_pipe_announcements(service, period, sample_size, download_pdfs)
│   │   └── persist_results(service, df, output_format='csv')
│   └── Return: Scrape summary statistics (total found, unique companies, time elapsed)
│
├── Interactive Cell (mode == "edit")
│   ├── Widgets:
│   │   ├── period_selector: Dropdown (today, week, month, 3months, 6months, all)
│   │   ├── sample_toggle: Checkbox (enable sample mode)
│   │   ├── sample_size_slider: Slider (10-500)
│   │   ├── download_pdfs_toggle: Checkbox
│   │   └── run_button: mo.ui.run_button()
│   ├── Preview Display:
│   │   ├── Show DataFrame head (10 rows)
│   │   ├── Summary statistics (total announcements, unique tickers)
│   │   └── Matched keywords distribution chart
│   └── Purpose: Interactive testing and parameter tuning
│
└── Script Execution Cell (mode == "script")
    ├── Parse parameters from deployment or defaults
    ├── run_pipe_scraper(output_dir, period, sample_size, download_pdfs, use_database)
    └── Purpose: Production execution via Prefect worker
```

**Flow Behavior:**

| Mode | Execution Context | Behavior |
|------|-------------------|----------|
| edit | `marimo edit notebooks/asx/asx_pipe_scraper.py` | Interactive widgets, live preview, manual run button |
| script | `python notebooks/asx/asx_pipe_scraper.py` | Execute flow with defaults, suitable for testing |
| prefect | Via deployment + worker | Scheduled execution, parameterized via prefect.yaml |

#### 2.2 Notebook: asx_announcement_scraper.py

**Purpose:** Fetch announcements for specific tickers over a time period.

**Structure:**

```
Notebook Structure:
│
├── PEP 723 Dependencies Block (same as pipe scraper)
│
├── app.setup Block
│   └── Imports (same pattern)
│
├── @app.function + @task: initialize_services
│   └── Same as pipe scraper
│
├── @app.function + @task: scrape_target_announcements
│   ├── Input: service, tickers (List[str]), period, download_pdfs
│   ├── Output: DataFrame with announcements
│   ├── Logic: Call service.scrape_target_announcements()
│   └── Validation: Check if tickers are valid ASX codes
│
├── @app.function + @task: persist_results
│   └── Same pattern as pipe scraper, supports CSV and JSON formats
│
├── @app.function + @flow: run_announcement_scraper
│   ├── Parameters: tickers, period, output_dir, download_pdfs, output_format, use_database
│   ├── Orchestration:
│   │   ├── service = initialize_services(output_dir, use_database)
│   │   ├── df = scrape_target_announcements(service, tickers, period, download_pdfs)
│   │   └── persist_results(service, df, output_format)
│   └── Return: Scrape summary (announcements per ticker, price-sensitive count)
│
├── Interactive Cell (mode == "edit")
│   ├── Widgets:
│   │   ├── ticker_input: mo.ui.text_area(label="Tickers (comma-separated)", value="CBA,NAB,BHP")
│   │   ├── period_selector: Dropdown
│   │   ├── download_pdfs_toggle: Checkbox
│   │   ├── format_selector: Radio buttons (csv, json, both)
│   │   └── run_button: mo.ui.run_button()
│   ├── Display:
│   │   ├── Results table with price-sensitive highlighting
│   │   ├── Timeline chart (announcements over time)
│   │   └── Download links for generated files
│   └── Purpose: Quick ticker lookup during development
│
└── Script Execution Cell (mode == "script")
    └── run_announcement_scraper(tickers, period, output_dir, download_pdfs, output_format, use_database)
```

**Ticker Validation:**

```
Validation Strategy:
├── Check ticker format (2-5 uppercase letters)
├── Optionally validate against ASX company list (get_listed_companies)
├── Log warnings for invalid tickers but continue processing valid ones
└── Raise error only if all tickers are invalid
```

#### 2.3 Notebook: asx_appendix5b_scraper.py

**Purpose:** Scrape today's Appendix 5B and Quarterly Activities reports, extract Section 8 financial data.

**Structure:**

```
Notebook Structure:
│
├── PEP 723 Dependencies Block (same)
│
├── app.setup Block (same)
│
├── @app.function + @task: initialize_services
│   └── Same pattern
│
├── @app.function + @task: scrape_appendix5b_reports
│   ├── Input: service, download_pdfs
│   ├── Output: ScrapeSummary (Pydantic model)
│   ├── Logic: Call service.scrape_appendix5b_reports()
│   └── Extraction: Section 8 data (items 8.6, 8.7)
│
├── @app.function + @task: persist_summary
│   ├── Input: service, summary (ScrapeSummary)
│   ├── Output: Path to summary JSON file
│   ├── Logic:
│   │   ├── Save summary JSON to output/summary_YYYYMMDD_HHMMSS.json
│   │   ├── Save individual result JSONs to output/json/
│   │   └── Optionally persist to database if service has db
│   └── Purpose: Structured output for downstream processing
│
├── @app.function + @flow: run_appendix5b_scraper
│   ├── Parameters: output_dir, download_pdfs, use_database
│   ├── Orchestration:
│   │   ├── service = initialize_services(output_dir, use_database)
│   │   ├── summary = scrape_appendix5b_reports(service, download_pdfs)
│   │   └── persist_summary(service, summary)
│   └── Return: Extraction statistics (total found, successful extractions, warnings)
│
├── Interactive Cell (mode == "edit")
│   ├── Widgets:
│   │   ├── download_pdfs_toggle: Checkbox
│   │   └── run_button: mo.ui.run_button()
│   ├── Display:
│   │   ├── Summary table (ticker, headline, 8.6 funding, 8.7 quarters)
│   │   ├── Warnings/Errors list
│   │   ├── Funding availability chart (bar chart of 8.6 values by ticker)
│   │   └── Extraction success rate
│   └── Purpose: Monitor daily cash flow report extraction
│
└── Script Execution Cell (mode == "script")
    └── run_appendix5b_scraper(output_dir, download_pdfs, use_database)
```

**Section 8 Extraction Display:**

The interactive mode will visualize:

```
Visualization Components:
├── Funding Table
│   ├── Columns: Ticker, Headline, Total Funding ($A'000), Est. Quarters
│   ├── Sorting: By funding amount (descending)
│   └── Styling: Highlight low funding (<500k) or short runway (<1.5 quarters)
│
├── Extraction Warnings Panel
│   ├── Group by warning type (PDF download fail, Section 8 not found, value extraction fail)
│   └── Show ticker and headline for each warning
│
└── Success Metrics Card
    ├── Total announcements found
    ├── Successful extractions (count and %)
    └── Warnings count
```

---

### 3. Prefect Deployment Configuration

Update `prefect.yaml` to include the three new ASX scraper deployments.

**Deployment Definitions:**

```
Deployment: asx-pipe-scraper-daily
├── Entrypoint: notebooks/asx/asx_pipe_scraper.py:run_pipe_scraper
├── Parameters:
│   ├── output_dir: "./outputs/pipe"
│   ├── period: "week"
│   ├── sample_size: null (scan all companies)
│   ├── download_pdfs: false (metadata only for daily scan)
│   └── use_database: true
├── Work Pool: windows-process-pool
├── Schedule: cron: "0 18 * * 1-5" (6 PM weekdays, after market close)
└── Timezone: "Australia/Sydney"

Deployment: asx-announcement-scraper-watchlist
├── Entrypoint: notebooks/asx/asx_announcement_scraper.py:run_announcement_scraper
├── Parameters:
│   ├── tickers: ["CBA", "NAB", "BHP", "RIO", "WES"] (configurable watchlist)
│   ├── period: "today"
│   ├── output_dir: "./outputs/watchlist"
│   ├── download_pdfs: true
│   ├── output_format: "both" (CSV + JSON)
│   └── use_database: true
├── Work Pool: windows-process-pool
├── Schedule: cron: "30 9,13,16 * * 1-5" (9:30 AM, 1:30 PM, 4:30 PM weekdays)
└── Timezone: "Australia/Sydney"

Deployment: asx-appendix5b-scraper-daily
├── Entrypoint: notebooks/asx/asx_appendix5b_scraper.py:run_appendix5b_scraper
├── Parameters:
│   ├── output_dir: "./outputs/appendix5b"
│   ├── download_pdfs: true
│   └── use_database: true
├── Work Pool: windows-process-pool
├── Schedule: cron: "0 10,14,17 * * 1-5" (10 AM, 2 PM, 5 PM weekdays)
└── Timezone: "Australia/Sydney"
```

**Schedule Rationale:**

| Deployment | Frequency | Timing Rationale |
|------------|-----------|------------------|
| PIPE Scraper | Daily (6 PM) | End of trading day scan for placement announcements |
| Announcement Watchlist | 3x daily (9:30 AM, 1:30 PM, 4:30 PM) | Capture morning pre-market, midday, and closing announcements |
| Appendix 5B | 3x daily (10 AM, 2 PM, 5 PM) | Quarterly reports often released morning, afternoon, or end of day |

---

### 4. Testing Strategy

#### 4.1 Unit Test Structure

Create comprehensive unit tests under `tests/unit/asx_scraper/`:

```
Test File Organization:
│
├── test_asx_scraper_service.py
│   ├── Test Initialization
│   │   ├── test_service_init_without_database
│   │   ├── test_service_init_with_database
│   │   └── test_output_directory_creation
│   │
│   ├── Test Company Operations
│   │   ├── test_get_listed_companies_success
│   │   ├── test_get_listed_companies_http_error
│   │   └── test_get_listed_companies_empty_response
│   │
│   ├── Test Target Announcements
│   │   ├── test_scrape_target_announcements_single_ticker
│   │   ├── test_scrape_target_announcements_multiple_tickers
│   │   ├── test_scrape_target_announcements_with_download
│   │   └── test_scrape_target_announcements_with_database_persistence
│   │
│   ├── Test PIPE Announcements
│   │   ├── test_scrape_pipe_announcements_no_matches
│   │   ├── test_scrape_pipe_announcements_with_keywords
│   │   ├── test_scrape_pipe_announcements_sample_mode
│   │   └── test_scrape_pipe_announcements_database_save
│   │
│   └── Test Appendix 5B
│       ├── test_scrape_appendix5b_success
│       ├── test_scrape_appendix5b_section8_extraction
│       ├── test_scrape_appendix5b_pdf_download_failure
│       └── test_scrape_appendix5b_database_persistence
│
├── test_http_client.py
│   ├── test_session_creation_with_retries
│   ├── test_request_with_delay
│   ├── test_accept_terms_and_redirect
│   └── test_request_timeout_handling
│
├── test_html_parser.py
│   ├── test_parse_company_list_csv
│   ├── test_parse_announcements_table
│   ├── test_parse_empty_announcements
│   └── test_parse_malformed_html
│
├── test_pdf_handler.py
│   ├── test_download_pdf_success
│   ├── test_download_pdf_with_terms_agreement
│   ├── test_extract_text_from_pdf_pymupdf
│   ├── test_extract_text_from_pdf_pdfplumber_fallback
│   ├── test_extract_section8_text_parsing
│   ├── test_extract_section8_table_parsing
│   └── test_extract_section8_not_found
│
├── test_filters.py
│   ├── test_is_pipe_announcement_positive_cases
│   ├── test_is_pipe_announcement_negative_cases
│   ├── test_filter_by_year
│   └── test_filter_by_date_range
│
└── test_models.py
    ├── test_announcement_model_validation
    ├── test_section8_model_validation
    ├── test_scrape_result_model
    └── test_scrape_summary_model
```

#### 4.2 Mocking Strategy

```
Mock Dependencies:
│
├── HTTP Requests (requests.Session)
│   ├── Mock: requests.Session.get, requests.Session.post
│   ├── Response: Mock HTML content, CSV data, PDF binary
│   └── Scenarios: Success, HTTP errors (500, 502, 504), timeouts
│
├── File System (pathlib.Path, open)
│   ├── Mock: Path.exists, Path.read_text, open (for PDF writing)
│   └── Scenarios: File exists, file not found, write permissions
│
├── PDF Libraries (fitz, pdfplumber)
│   ├── Mock: fitz.open, pdfplumber.open
│   ├── Response: Mock extracted text, table data
│   └── Scenarios: Successful extraction, extraction failure, corrupted PDF
│
├── Database Service
│   ├── Mock: database_service.execute_query_from_file
│   ├── Response: Mock DataFrame (empty for INSERT operations)
│   └── Scenarios: Successful insert, database connection error, SQL syntax error
│
└── Time-Sensitive Operations
    ├── Mock: datetime.now, time.sleep
    └── Purpose: Deterministic testing, avoid actual delays
```

**Example Test Pattern:**

```
Test: test_scrape_pipe_announcements_with_keywords
│
├── Setup Mocks
│   ├── Mock session.get to return company CSV
│   ├── Mock session.get to return announcement HTML (with PIPE keywords)
│   └── Mock database_service.execute_query_from_file
│
├── Execute
│   ├── service = AsxScraperService(output_dir='/tmp', database_service=mock_db)
│   ├── df = service.scrape_pipe_announcements(period='M6', save_to_db=True)
│
├── Assertions
│   ├── Assert df is not empty
│   ├── Assert all headlines contain PIPE keywords
│   ├── Assert database insert was called with correct parameters
│   └── Assert CSV file was created in output_dir
│
└── Cleanup
    └── Remove temporary output directory
```

#### 4.3 Smoke Tests

Create `tests/smoke_test_asx_notebooks.py` to validate notebooks can execute:

```
Smoke Test Strategy:
│
├── Notebook Import Test
│   ├── Test: Import each notebook as module
│   ├── Validation: No import errors, flow function exists
│   └── Purpose: Ensure decorator stacking and imports are correct
│
├── Flow Execution Test (Mocked)
│   ├── Test: Execute flow with mocked AsxScraperService
│   ├── Validation: Flow completes without errors, tasks are called
│   └── Purpose: Validate Prefect orchestration logic
│
└── Marimo Validation Test
    ├── Test: Run `marimo check notebooks/asx/`
    ├── Validation: No syntax errors, mode-conditional logic valid
    └── Purpose: Ensure notebooks are valid Marimo files
```

**Smoke Test Execution:**

```
Test Execution Flow:
├── Pre-test Setup
│   ├── Create temporary output directory
│   └── Mock all external dependencies (HTTP, database, PDF libraries)
│
├── Test 1: asx_pipe_scraper.py
│   ├── Import notebook module
│   ├── Mock AsxScraperService.scrape_pipe_announcements to return empty DataFrame
│   ├── Execute run_pipe_scraper(sample_size=1, use_database=False)
│   └── Assert: Flow completes, no exceptions
│
├── Test 2: asx_announcement_scraper.py
│   ├── Import notebook module
│   ├── Mock AsxScraperService.scrape_target_announcements to return empty DataFrame
│   ├── Execute run_announcement_scraper(tickers=['TEST'], use_database=False)
│   └── Assert: Flow completes, no exceptions
│
├── Test 3: asx_appendix5b_scraper.py
│   ├── Import notebook module
│   ├── Mock AsxScraperService.scrape_appendix5b_reports to return ScrapeSummary
│   ├── Execute run_appendix5b_scraper(use_database=False)
│   └── Assert: Flow completes, summary JSON created
│
└── Cleanup
    └── Remove temporary output directory
```

---

### 5. SQL File Adoption Strategy

#### 5.1 SQL File Migration

**Current Location:** `asx/sql/`  
**Proposed Action:** Keep in place, reference from service

```
SQL File Usage in AsxScraperService:
│
├── File Path Resolution
│   ├── Base Path: asx/sql/
│   ├── Resolution: Path(__file__).parent.parent.parent / "asx" / "sql"
│   └── Validation: Check file exists before database call
│
├── Parameter Binding Strategy
│   ├── Named Parameters (PostgreSQL :param style)
│   ├── Conversion: Pydantic model → dict → named params
│   └── Example:
│       Announcement model:
│         ticker='CBA', datetime='14/12/2025 8:30 PM', headline='...'
│       →
│       SQL params:
│         ticker='CBA', announcement_date='2025-12-14', 
│         announcement_time='20:30', headline='...'
│
└── Error Handling
    ├── FileNotFoundError: Log error, skip database save
    ├── Database Exception: Log warning, continue flow (graceful degradation)
    └── Parameter Mismatch: Validate model fields match SQL placeholders
```

#### 5.2 SQL Parameter Transformation

```
Transformation Rules:
│
├── Announcement Table (create_announcement.sql)
│   ├── datetime → announcement_date (DATE) + announcement_time (TIME)
│   │   └── Split: "14/12/2025 8:30 PM" → date='2025-12-14', time='20:30:00'
│   ├── price_sensitive (bool) → is_price_sensitive (BOOLEAN)
│   └── pdf_link → pdf_url (TEXT)
│
├── PIPE Table (create_pipe_announcement.sql)
│   ├── matched_keywords (List[str]) → description (TEXT, comma-separated)
│   ├── datetime (str) → announcement_datetime (TIMESTAMP)
│   └── No transformation: ticker, company_name, title, pdf_link, is_price_sensitive
│
└── Appendix 5B Table (create_appendix_5b_report.sql)
    ├── section_8_data.item_8_6 → total_available_funding (DECIMAL)
    ├── section_8_data.item_8_7 → estimated_quarters_funding (DECIMAL or TEXT for 'N/A')
    ├── matched_keywords (List[str]) → matched_keywords (TEXT, JSON array string)
    ├── warning (str) → extraction_warnings (TEXT)
    └── date (str 'YYYY_MM_DD') → report_date (DATE, parse and convert)
```

**Helper Method Design:**

```
Method: _prepare_sql_params(model, table_type) → dict
│
├── Input: Pydantic model instance, table type identifier
├── Output: Dictionary with SQL-compatible parameter names and values
│
├── Logic:
│   ├── Extract model fields: model.model_dump()
│   ├── Apply table-specific transformations (switch on table_type)
│   ├── Convert Python types to SQL types (datetime parsing, list to string)
│   └── Validate all required SQL parameters are present
│
└── Error Handling:
    ├── Missing field: Raise ValueError with helpful message
    └── Type mismatch: Log warning, attempt conversion
```

---

### 6. Dependency Management

#### 6.1 New Dependencies

Add to `pyproject.toml`:

```
New Dependencies:
├── beautifulsoup4>=4.12.0 (HTML parsing)
├── pymupdf>=1.23.0 (PDF text extraction, primary method)
├── pdfplumber>=0.10.0 (PDF table extraction, fallback method)
└── requests>=2.31.0 (already in project, ensure compatibility)
```

**Rationale:**
- `beautifulsoup4`: Required for HTML announcement parsing
- `pymupdf` (fitz): Fast PDF text extraction, primary method
- `pdfplumber`: Table-aware PDF extraction, fallback for Section 8 data
- `requests`: HTTP client (already in use, no addition needed)

#### 6.2 Notebook PEP 723 Blocks

Each notebook will specify inline dependencies:

```
Inline Dependency Block (PEP 723):
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.10.9",
#     "prefect>=3.0.0",
#     "pandas>=2.0.0",
#     "beautifulsoup4>=4.12.0",
#     "pymupdf>=1.23.0",
#     "pdfplumber>=0.10.0",
#     "requests>=2.31.0",
#     "pydantic>=2.0.0",
# ]
# ///
```

**Purpose:**
- Self-contained notebooks with explicit dependencies
- Compatible with `marimo run` and `python notebook.py`
- No reliance on global environment (portable)

---

### 7. Migration Checklist

#### 7.1 Service Layer Tasks

| Task | Description | Validation Criteria |
|------|-------------|---------------------|
| Create service structure | Establish `src/services/asx_scraper/` with 6 modules | All modules importable, no circular dependencies |
| Implement http_client.py | Session management, retry logic, terms acceptance | Unit tests pass, mock HTTP calls successful |
| Implement html_parser.py | BeautifulSoup parsing for companies and announcements | Parse test HTML fixtures correctly |
| Implement pdf_handler.py | PDF download, text extraction, Section 8 parsing | Extract text from test PDFs, parse Section 8 data |
| Implement models.py | Pydantic models for all data structures | Model validation tests pass, serialization works |
| Implement filters.py | PIPE keyword matching, date filtering | Filter logic tests pass for positive/negative cases |
| Implement asx_scraper_service.py | Main orchestrator with 3 high-level workflows | Integration with all submodules, database optional |
| Add SQL parameter helpers | Transform Pydantic models to SQL params | Parameter dicts match SQL placeholders |
| Implement database integration | Use SQL files via database_service | Insert operations successful, idempotent (ON CONFLICT) |

#### 7.2 Notebook Tasks

| Task | Description | Validation Criteria |
|------|-------------|---------------------|
| Create asx_pipe_scraper.py | Marimo notebook with flow for PIPE scraping | Notebook runs in edit mode, flow executes in script mode |
| Create asx_announcement_scraper.py | Notebook for target ticker scraping | Interactive widgets work, flow deploys successfully |
| Create asx_appendix5b_scraper.py | Notebook for Appendix 5B scraping | Section 8 extraction visible in edit mode, flow scheduled |
| Add interactive widgets | UI elements for all notebooks | Widgets responsive, parameter changes trigger updates |
| Implement mode-conditional logic | Separate edit and script execution paths | Edit mode shows UI, script mode runs flow automatically |
| Validate decorator stacking | @app.function before @task/@flow | No decorator errors, functions exportable |

#### 7.3 Testing Tasks

| Task | Description | Validation Criteria |
|------|-------------|---------------------|
| Write unit tests for http_client | Mock requests, test retry logic | All tests pass, 100% coverage of http_client.py |
| Write unit tests for html_parser | Test BeautifulSoup parsing | All tests pass, handle malformed HTML |
| Write unit tests for pdf_handler | Mock PDF libraries, test extraction | All tests pass, fallback logic works |
| Write unit tests for filters | Test PIPE keywords, date filtering | All tests pass, edge cases covered |
| Write unit tests for service | Mock all dependencies, test workflows | All tests pass, database optional behavior correct |
| Write unit tests for models | Pydantic validation tests | All tests pass, serialization/deserialization works |
| Write smoke tests for notebooks | Import notebooks, execute flows with mocks | All notebooks importable, flows execute without errors |
| Validate test coverage | Ensure >80% coverage for service layer | Coverage report shows >80% for asx_scraper/ |

#### 7.4 Deployment Tasks

| Task | Description | Validation Criteria |
|------|-------------|---------------------|
| Update prefect.yaml | Add 3 deployment definitions | Deployments visible in `prefect deployment ls` |
| Configure work pool | Ensure windows-process-pool exists | Worker can pick up jobs from pool |
| Test deployment | Run `prefect deploy --all` | All deployments created without errors |
| Trigger test runs | Manually trigger each deployment | Flows execute successfully, logs visible in Prefect UI |
| Validate schedules | Check cron expressions | Schedules align with Australian market hours |
| Test parameter overrides | Trigger with custom parameters | Flows respect parameter changes |

---

### 8. Feature Preservation Validation

#### 8.1 PIPE Scraper Features

| Original Feature | Implementation in Service | Validation Method |
|------------------|---------------------------|-------------------|
| Scan all ASX companies | `get_listed_companies()` method | Test with mock CSV, verify all companies returned |
| PIPE keyword matching | `filters.is_pipe_announcement()` | Test all 21 keywords, verify case-insensitive match |
| Sample mode | `scrape_pipe_announcements(sample_size=N)` | Test with sample_size=10, verify only 10 companies scanned |
| Year filtering | `filters.filter_by_year()` | Test date range filtering, verify correct years retained |
| CSV output | `persist_results()` task | Verify CSV structure matches original output |
| Progress logging | Logger calls in scrape loop | Check log output for progress messages (X/Total) |
| Delay between requests | `http_client` delay parameter | Mock time.sleep, verify delay is respected |

#### 8.2 Announcement Scraper Features

| Original Feature | Implementation in Service | Validation Method |
|------------------|---------------------------|-------------------|
| Ticker-specific search | `scrape_target_announcements(tickers)` | Test with multiple tickers, verify separate queries |
| Period selection | `period` parameter (T, W, M3, M6, A) | Test all period codes, verify URL params correct |
| PDF download | `pdf_handler.download_pdf()` | Mock PDF binary, verify file saved to correct path |
| Terms acceptance handling | `http_client.accept_terms_and_get_pdf_url()` | Mock terms page HTML, verify form submission |
| Price-sensitive flag | `Announcement.price_sensitive` | Verify parsed from HTML, included in output |
| CSV and JSON output | `persist_results(output_format)` | Test both formats, verify data integrity |

#### 8.3 Appendix 5B Scraper Features

| Original Feature | Implementation in Service | Validation Method |
|------------------|---------------------------|-------------------|
| Keyword matching | Filter for 'quarterly activities', 'cash flow report', 'appendix 5b' | Test with mock announcements, verify matching logic |
| PDF download | `pdf_handler.download_pdf()` | Same as announcement scraper |
| Text extraction | `pdf_handler.extract_text_from_pdf()` | Test with sample PDF, verify text content |
| Section 8 text parsing | `pdf_handler.extract_section8_data()` | Test with regex patterns, verify 8.6 and 8.7 extraction |
| Section 8 table parsing | `pdf_handler.extract_section8_with_tables()` | Test with pdfplumber mock, verify fallback works |
| Individual JSON output | `persist_summary()` saves per-announcement JSON | Verify JSON structure matches original format |
| Summary JSON | `ScrapeSummary` model → JSON | Verify summary includes all results, timestamps, stats |
| Warning tracking | `ScrapeResult.warning` field | Test extraction failures, verify warnings logged |

---

### 9. Data Flow Architecture

```
Data Flow Diagram (Mermaid):

┌─────────────────────────────────────────────────────────────────────┐
│                         PREFECT DEPLOYMENT                           │
│  (Scheduled trigger via prefect.yaml or manual run)                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      MARIMO NOTEBOOK (Script Mode)                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  @app.function + @flow: run_[scraper_type]                   │  │
│  │    ├─ Initialize AsxScraperService                           │  │
│  │    ├─ Execute scrape workflow (task)                         │  │
│  │    └─ Persist results (task)                                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ASX SCRAPER SERVICE                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  High-Level Workflow Methods                                │   │
│  │  ├─ scrape_target_announcements()                           │   │
│  │  ├─ scrape_pipe_announcements()                             │   │
│  │  └─ scrape_appendix5b_reports()                             │   │
│  └────────────┬────────────────────────────────────────────────┘   │
│               │                                                      │
│  ┌────────────▼─────────────┐  ┌────────────────────────────────┐ │
│  │   HTTP Client Module     │  │    HTML Parser Module          │ │
│  │  ├─ Fetch company CSV    │  │  ├─ Parse company list         │ │
│  │  ├─ Fetch announcements  │  │  ├─ Parse announcement table   │ │
│  │  └─ Handle ASX terms     │  │  └─ Extract metadata           │ │
│  └──────────────────────────┘  └────────────────────────────────┘ │
│               │                                │                     │
│  ┌────────────▼────────────────────────────────▼────────────────┐  │
│  │                    Filters Module                            │  │
│  │  ├─ PIPE keyword matching                                    │  │
│  │  ├─ Date range filtering                                     │  │
│  │  └─ Announcement classification                              │  │
│  └────────────┬─────────────────────────────────────────────────┘  │
│               │                                                      │
│  ┌────────────▼─────────────┐  ┌────────────────────────────────┐ │
│  │  PDF Handler Module      │  │  Models Module                 │ │
│  │  ├─ Download PDF         │  │  ├─ Announcement              │ │
│  │  ├─ Extract text          │  │  ├─ Company                   │ │
│  │  └─ Parse Section 8      │  │  ├─ Section8Data              │ │
│  │                           │  │  └─ ScrapeSummary             │ │
│  └──────────────────────────┘  └────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      OUTPUT DESTINATIONS                             │
│  ┌──────────────────────┐  ┌──────────────────────────────────────┐│
│  │  File System         │  │  Database (PostgreSQL)               ││
│  │  ├─ CSV reports      │  │  ├─ asx_announcements table          ││
│  │  ├─ JSON summaries   │  │  ├─ asx_pipe_announcements table     ││
│  │  └─ PDF files        │  │  └─ asx_appendix_5b_reports table    ││
│  └──────────────────────┘  └──────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

**Data Flow Explanation:**

1. **Trigger**: Prefect deployment schedules trigger notebook execution
2. **Orchestration**: Marimo notebook flow orchestrates tasks (initialize → scrape → persist)
3. **Execution**: AsxScraperService coordinates submodules (HTTP, parsing, PDF, filtering)
4. **Transformation**: Raw HTML/PDF data → Pydantic models → SQL parameters
5. **Persistence**: Dual output (file system for archival, database for querying)

---

### 10. Error Handling and Resilience

#### 10.1 Error Categories and Responses

```
Error Handling Strategy:
│
├── HTTP Errors (4xx, 5xx)
│   ├── Strategy: Retry with exponential backoff (3 attempts)
│   ├── Logging: Log error details, URL, status code
│   ├── Flow Behavior: Continue with next ticker/company, do not fail entire flow
│   └── User Feedback: Include in summary (warnings_count)
│
├── PDF Download Failures
│   ├── Strategy: Log warning, skip PDF (metadata still saved)
│   ├── Logging: Log PDF URL, error message
│   ├── Flow Behavior: Continue with next announcement
│   └── User Feedback: Mark in result as pdf_downloaded=False, add warning
│
├── PDF Extraction Failures
│   ├── Strategy: Attempt fallback (PyMuPDF → pdfplumber), then fail gracefully
│   ├── Logging: Log PDF path, extraction method attempted, error
│   ├── Flow Behavior: Continue with next PDF, mark extraction_success=False
│   └── User Feedback: Add warning "Failed to extract text from PDF"
│
├── Section 8 Data Not Found
│   ├── Strategy: Not an error (some reports lack Section 8), log info
│   ├── Logging: Log ticker, headline, "Section 8 not found"
│   ├── Flow Behavior: Continue normally
│   └── User Feedback: Mark section_8_found=False, no warning (expected)
│
├── Database Connection Errors
│   ├── Strategy: Log error, continue with file output only (graceful degradation)
│   ├── Logging: Log database error message, SQL file path
│   ├── Flow Behavior: Skip database persistence, do not fail flow
│   └── User Feedback: Log warning "Database unavailable, saved to file only"
│
└── Invalid Input Parameters
    ├── Strategy: Validate early, raise ValueError with helpful message
    ├── Logging: Log invalid parameter name and value
    ├── Flow Behavior: Fail flow immediately (prevents wasted execution)
    └── User Feedback: Clear error message, suggest valid values
```

#### 10.2 Prefect Task Configuration

```
Task Retry Configuration:
│
├── @task(retries=2, retry_delay_seconds=30)
│   └── Applied to: All HTTP-dependent tasks (scrape_* tasks)
│
├── @task(retries=0)
│   └── Applied to: persist_results (file I/O, should not retry)
│
└── @task(cache_key_fn=task_input_hash, cache_expiration=timedelta(hours=1))
    └── Optional: For get_listed_companies (infrequent changes)
```

**Rationale:**
- HTTP operations are transient failures → retry appropriate
- File I/O failures indicate system issues → retry unhelpful
- Company list changes rarely → caching reduces load on ASX servers

---

### 11. Performance Considerations

#### 11.1 Optimization Strategies

```
Performance Optimizations:
│
├── Request Throttling
│   ├── Default Delay: 0.5 seconds between requests
│   ├── Configurable: service = AsxScraperService(delay=0.3)
│   ├── Rationale: Avoid overwhelming ASX servers, prevent rate limiting
│   └── Implementation: time.sleep(delay) in http_client
│
├── PDF Download On-Demand
│   ├── Default: download_pdfs=False (metadata only)
│   ├── Use Case: Daily scans collect metadata, targeted runs download PDFs
│   ├── Rationale: Faster execution, reduced storage
│   └── Implementation: if download_pdfs: pdf_handler.download_pdf()
│
├── Sample Mode for Testing
│   ├── Parameter: sample_size=50 (default: scan all ~2000 companies)
│   ├── Use Case: Development testing, quick validation
│   ├── Rationale: 50 companies complete in ~30 seconds vs 20+ minutes
│   └── Implementation: random.sample(companies, sample_size)
│
├── Database Batch Inserts (Future Enhancement)
│   ├── Current: Individual INSERT per announcement
│   ├── Optimization: Batch INSERT (100 records per query)
│   ├── Rationale: Reduce database round trips
│   └── Implementation: Accumulate params, execute_many()
│
└── Concurrent PDF Downloads (Future Enhancement)
    ├── Current: Sequential download
    ├── Optimization: ThreadPoolExecutor for parallel downloads
    ├── Rationale: I/O-bound operation, benefit from concurrency
    └── Implementation: concurrent.futures.ThreadPoolExecutor
```

#### 11.2 Execution Time Estimates

| Workflow | Configuration | Estimated Duration | Notes |
|----------|---------------|-------------------|-------|
| PIPE Scraper (All Companies) | 2000 companies, metadata only | 20-25 minutes | 0.5s delay × 2000 requests |
| PIPE Scraper (Sample) | 50 companies, metadata only | 30-45 seconds | Quick testing |
| Announcement Scraper | 5 tickers, 1 week | 5-10 seconds | Fast, targeted |
| Appendix 5B Scraper | Daily (5-10 reports) | 2-5 minutes | Includes PDF download + extraction |

**Bottleneck Analysis:**
- HTTP requests: Primary bottleneck (network I/O)
- PDF extraction: Secondary bottleneck (CPU-bound for OCR-heavy PDFs)
- Database inserts: Minimal impact (local/LAN PostgreSQL)

---

### 12. Observability and Monitoring

#### 12.1 Logging Strategy

```
Logging Levels and Usage:
│
├── INFO Level
│   ├── Flow start/completion
│   ├── Major milestones (e.g., "Fetched 2000 companies", "Found 15 PIPE announcements")
│   ├── Database save operations
│   └── File output paths
│
├── WARNING Level
│   ├── HTTP errors (after retries exhausted)
│   ├── PDF download failures
│   ├── Section 8 data extraction issues
│   └── Database connection errors (graceful degradation)
│
├── DEBUG Level
│   ├── HTTP request details (URL, params)
│   ├── HTML parsing progress
│   ├── PDF extraction attempts
│   └── SQL parameter construction
│
└── ERROR Level
    ├── Unrecoverable flow failures
    ├── Invalid parameters (fail-fast scenarios)
    └── Unexpected exceptions
```

#### 12.2 Prefect Flow Metrics

```
Flow Return Values (Metrics):
│
├── PIPE Scraper Returns:
│   ├── total_announcements: int
│   ├── unique_companies: int
│   ├── execution_time_seconds: float
│   └── warnings_count: int
│
├── Announcement Scraper Returns:
│   ├── total_announcements: int
│   ├── announcements_per_ticker: dict[str, int]
│   ├── price_sensitive_count: int
│   └── downloaded_pdfs: int (if download_pdfs=True)
│
└── Appendix 5B Scraper Returns:
    ├── total_reports_found: int
    ├── successful_extractions: int
    ├── extraction_success_rate: float (percentage)
    └── warnings: List[str]
```

**Rationale:**
- Return values visible in Prefect UI for quick status checks
- Enables alerting on anomalies (e.g., sudden drop in announcements)
- Provides audit trail for data quality validation

#### 12.3 Alerting Recommendations (Future)

```
Alerting Scenarios (to be implemented via Prefect Automations):
│
├── Flow Failure Alert
│   ├── Trigger: Flow state = FAILED
│   ├── Action: Email/Slack notification to data team
│   └── Priority: High
│
├── Low Data Volume Alert
│   ├── Trigger: Appendix 5B scraper returns 0 reports (unusual on trading days)
│   ├── Action: Email notification
│   └── Priority: Medium
│
├── High Warning Count Alert
│   ├── Trigger: warnings_count > 20% of total_announcements
│   ├── Action: Log to monitoring dashboard
│   └── Priority: Low
│
└── Database Unavailability Alert
    ├── Trigger: Database connection error logged
    ├── Action: Email to infrastructure team
    └── Priority: Medium
```

---

### 13. Implementation Sequence

**Phase 1: Service Layer Foundation (Week 1)**

1. Create `src/services/asx_scraper/` directory structure
2. Implement `models.py` (Pydantic models)
3. Implement `http_client.py` (session, retry logic)
4. Implement `html_parser.py` (BeautifulSoup parsing)
5. Write unit tests for models, http_client, html_parser
6. Validate: All unit tests pass, mock HTTP requests successful

**Phase 2: PDF and Filtering Logic (Week 1)**

7. Implement `pdf_handler.py` (download, text extraction, Section 8 parsing)
8. Implement `filters.py` (PIPE keywords, date filtering)
9. Write unit tests for pdf_handler, filters
10. Validate: PDF extraction works with test files, keyword matching accurate

**Phase 3: Service Orchestration (Week 2)**

11. Implement `asx_scraper_service.py` (main orchestrator)
12. Implement three high-level workflow methods (target, PIPE, Appendix 5B)
13. Add SQL parameter transformation helpers
14. Write integration-style unit tests (mocked dependencies)
15. Validate: Service methods return expected DataFrames/Summaries

**Phase 4: Database Integration (Week 2)**

16. Test SQL files with PostgreSQL (manual verification)
17. Implement database save methods in service
18. Test database integration with mocked database_service
19. Validate: SQL parameters correct, ON CONFLICT works

**Phase 5: Marimo Notebooks (Week 3)**

20. Create `notebooks/asx/asx_pipe_scraper.py` notebook
21. Create `notebooks/asx/asx_announcement_scraper.py` notebook
22. Create `notebooks/asx/asx_appendix5b_scraper.py` notebook
23. Add interactive widgets and visualizations
24. Validate: Notebooks run in `marimo edit`, widgets responsive

**Phase 6: Prefect Integration (Week 3)**

25. Add flow decorators and mode-conditional logic to notebooks
26. Test flows in script mode (`python notebook.py`)
27. Write smoke tests for notebooks
28. Validate: Flows execute without errors, decorator stacking correct

**Phase 7: Deployment and Testing (Week 4)**

29. Update `prefect.yaml` with three deployments
30. Deploy to Prefect: `prefect deploy --all`
31. Trigger manual test runs for each deployment
32. Run smoke tests in CI/CD pipeline (if available)
33. Validate: Scheduled runs work, logs visible in Prefect UI

**Phase 8: Documentation and Handoff (Week 4)**

34. Update project README with ASX scraper documentation
35. Document database schema and SQL file usage
36. Create runbook for common issues (HTTP errors, PDF extraction failures)
37. Validate: Team can operate and troubleshoot scrapers independently

---

### 14. Risk Assessment and Mitigation

| Risk | Likelihood | Impact | Mitigation Strategy |
|------|-----------|--------|---------------------|
| ASX website structure changes | Medium | High | Use defensive parsing (try/except), log parsing failures, monitor for sudden data drops |
| PDF format variations | High | Medium | Dual-extraction strategy (text + tables), graceful degradation, manual review flagged cases |
| Rate limiting by ASX | Low | Medium | Configurable delay, exponential backoff, monitor HTTP 429 responses |
| Database unavailable | Low | Low | Graceful degradation (file output only), alerting for infrastructure issues |
| Dependency version conflicts | Low | Medium | Pin versions in pyproject.toml, test upgrades in staging environment |
| Large PDF files exhaust memory | Low | Medium | Stream PDF downloads (chunks), set max file size limit (e.g., 50MB) |
| Incorrect Section 8 extraction | Medium | Medium | Validate extracted values (range checks), flag outliers for manual review, improve regex patterns iteratively |
| Timezone issues (AU vs UTC) | Low | Low | Use `Australia/Sydney` timezone explicitly, convert timestamps consistently |

---

## Confidence Assessment

**Confidence Level:** High

**Basis for Confidence:**

1. **Clear Requirements:** User provided specific steps, reference files, and desired outcomes
2. **Proven Architecture:** Follows established Prefect + Marimo patterns already in project (see `prefect_workflow_sample.py`)
3. **Existing Infrastructure:** Database service pattern, SQL files, testing patterns already exist
4. **Modular Design:** Service decomposition into small, testable components reduces complexity
5. **Feature Preservation:** Detailed validation checklist ensures no loss of existing functionality
6. **Risk Mitigation:** Identified potential issues with concrete mitigation strategies

**Key Success Factors:**

- Reuse of existing `MSSQLService` interface pattern simplifies database integration
- Pydantic models provide type safety and validation throughout the pipeline
- Mode-conditional execution (edit vs. script) enables rapid development iteration
- Comprehensive unit testing with mocking ensures testability without external dependencies
- SQL file reuse maintains data consistency and reduces duplication

# ASX PIPE Scraper - LLM Coder Guide

## Overview

The ASX PIPE Scraper is a unified Marimo + Prefect notebook that scans Australian Securities Exchange (ASX) companies for PIPE (Private Investment in Public Equity) announcements and capital raising activities. It operates in dual modes: interactive development and production execution.

**File Location:** `notebooks/asx/asx_pipe_scraper.py`

**Flow Name:** `asx-pipe-scraper`

---

## Purpose

Automatically identifies and collects announcements related to:
- Private placements
- Capital raising activities
- Share placements
- Equity raises
- Institutional placements
- Rights issues
- Share purchase plans (SPP)
- Entitlement offers

**Use Cases:**
- Market surveillance for capital raising activities
- Investment opportunity identification
- Competitor analysis
- Regulatory monitoring

---

## Architecture

### Unified Design Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                    ASX PIPE SCRAPER NOTEBOOK                     │
├─────────────────────────────────────────────────────────────────┤
│  MARIMO NOTEBOOK (Single File)                                  │
│  ├─ Interactive Mode (marimo edit)                              │
│  │  ├─ Widgets & UI Controls                                    │
│  │  ├─ Live Data Preview                                        │
│  │  └─ Visualization                                            │
│  │                                                               │
│  ├─ Script Mode (python/prefect execution)                      │
│  │  ├─ Production Flow Execution                                │
│  │  ├─ Scheduled Runs                                           │
│  │  └─ Automated Data Collection                                │
│  │                                                               │
│  └─ @app.function + @flow/@task Decorators                      │
│     ├─ Prefect Orchestration                                    │
│     ├─ Task Retry Logic                                         │
│     └─ Logging & Monitoring                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Execution Modes

| Mode | Command | Purpose | UI | Database |
|------|---------|---------|-----|----------|
| **Interactive** | `marimo edit notebooks/asx/asx_pipe_scraper.py` | Development & testing | ✅ Yes | Optional |
| **Script** | `python notebooks/asx/asx_pipe_scraper.py` | CLI execution | ❌ No | Optional |
| **Prefect** | Via deployment | Production/scheduled | ❌ No | Yes |

---

## Flow Structure

### Tasks

#### 1. `initialize_services`
```python
@app.function
@task(retries=2, retry_delay_seconds=30)
def initialize_services(output_dir: str, use_database: bool):
    """Initialize ASX scraper service with optional database."""
```

**Purpose:** Set up AsxScraperService with database connection (if enabled)

**Inputs:**
- `output_dir`: Directory for output files
- `use_database`: Whether to enable database persistence

**Outputs:** Configured `AsxScraperService` instance

**Error Handling:** Database initialization failures are logged as warnings; service continues without database

---

#### 2. `scrape_pipe_announcements_task`
```python
@app.function
@task(retries=2, retry_delay_seconds=30)
def scrape_pipe_announcements_task(
    service: AsxScraperService, 
    period: str, 
    sample_size: int, 
    download_pdfs: bool
):
```

**Purpose:** Scan ASX companies and identify PIPE announcements

**Process:**
1. Fetch ASX company list (~2000 companies)
2. For each company (or sample):
   - Fetch announcements for specified period
   - Check headlines against 21 PIPE keywords
   - Collect matching announcements
3. Optionally download PDFs
4. Save to database if enabled

**Inputs:**
- `service`: AsxScraperService instance
- `period`: Time period (`today`, `week`, `month`, `3months`, `6months`, `all`)
- `sample_size`: Number of companies to scan (0 = all companies)
- `download_pdfs`: Whether to download announcement PDFs

**Outputs:** DataFrame with matched PIPE announcements

**Performance:**
- Full scan (~2000 companies): 15-20 minutes
- Sample (50 companies): 30-60 seconds

---

#### 3. `persist_results`
```python
@app.function
@task
def persist_results(service: AsxScraperService, df, output_format: str):
    """Persist results to CSV."""
```

**Purpose:** Save results to file system

**Outputs:**
- CSV file: `outputs/pipe/csv/asx_pipe_announcements_YYYYMMDD_HHMMSS.csv`
- Optional JSON: `outputs/pipe/json/asx_pipe_announcements_YYYYMMDD_HHMMSS.json`

---

### Main Flow

```python
@app.function
@flow(name="asx-pipe-scraper", log_prints=True)
def run_pipe_scraper(
    output_dir: str = "./outputs/pipe",
    period: str = "week",
    sample_size: int = 0,
    download_pdfs: bool = False,
    use_database: bool = False
):
```

**Orchestration:**
1. Initialize services → Scrape PIPE announcements → Persist results
2. Calculate execution statistics
3. Return summary metrics

**Returns:**
```python
{
    "total_announcements": int,      # Number of PIPE announcements found
    "unique_companies": int,          # Number of companies with PIPE announcements
    "execution_time_seconds": float,  # Execution time
    "saved_files": list               # Paths to saved files
}
```

---

## Usage Patterns

### 1. Interactive Development (Marimo Edit Mode)

```bash
marimo edit notebooks/asx/asx_pipe_scraper.py
```

**Features Available:**
- **Period Selector:** Choose time range (today, week, month, 3months, 6months, all)
- **Sample Mode:** Test with subset of companies (10-500)
- **Download PDFs:** Toggle PDF download
- **Database Toggle:** Enable/disable database persistence
- **Run Button:** Execute flow interactively
- **Live Results:** View DataFrame with matched announcements
- **Statistics:** Total announcements, unique companies

**Typical Workflow:**
1. Open notebook in edit mode
2. Enable sample mode (50 companies)
3. Select period (e.g., "week")
4. Disable PDF downloads for faster testing
5. Click "Run PIPE Scraper"
6. Review results table
7. Adjust parameters and rerun

---

### 2. CLI Execution (Script Mode)

```bash
# Run with default parameters
python notebooks/asx/asx_pipe_scraper.py

# Default behavior:
# - output_dir: ./outputs/pipe
# - period: week
# - sample_size: 0 (all companies)
# - download_pdfs: False
# - use_database: True
```

**When to Use:**
- One-off data collection
- Manual execution outside Prefect
- Testing in production-like environment

---

### 3. Prefect Production Deployment

#### Deployment Configuration

**File:** `prefect.yaml`

```yaml
deployments:
  - name: asx-pipe-scraper-daily
    entrypoint: notebooks/asx/asx_pipe_scraper.py:run_pipe_scraper
    parameters:
      output_dir: "./outputs/pipe"
      period: "week"
      sample_size: 0           # Scan all companies
      download_pdfs: false     # Metadata only (faster)
      use_database: true
    work_pool:
      name: windows-process-pool
    schedules:
      - cron: "0 18 * * 1-5"   # 6 PM weekdays (after market close)
        timezone: "Australia/Sydney"
```

#### Deploy to Prefect

```bash
# Deploy all flows
prefect deploy --all

# Deploy specific flow
prefect deploy --name asx-pipe-scraper-daily

# Verify deployment
prefect deployment ls
```

#### Manual Trigger

```bash
# Trigger via Prefect CLI
prefect deployment run 'asx-pipe-scraper/asx-pipe-scraper-daily'

# With custom parameters
prefect deployment run 'asx-pipe-scraper/asx-pipe-scraper-daily' \
  --param period=month \
  --param download_pdfs=true
```

#### Start Worker

```bash
# Start worker to execute scheduled flows
prefect worker start --pool windows-process-pool --type process
```

---

## PIPE Keyword Matching

The scraper matches announcements against **21 PIPE-related keywords**:

### Primary Keywords
- `placement`
- `private placement`
- `capital raising`
- `capital raise`
- `share placement`
- `equity raising`
- `equity raise`

### Secondary Keywords
- `share issue`
- `securities issue`
- `institutional placement`
- `strategic placement`
- `share subscription`
- `convertible note`
- `fund raising`
- `fundraising`
- `share offer`
- `new shares`
- `issue of shares`
- `issue of securities`
- `proposed issue of securities`
- `proposed issue`

### Entitlement/Rights
- `entitlement offer`
- `rights issue`
- `share purchase plan`
- `spp`
- `accelerated non-renounceable`
- `non-renounceable entitlement`
- `renounceable entitlement`
- `underwritten placement`
- `completion of placement`
- `successful placement`
- `institutional offer`
- `retail offer`

**Matching Logic:**
- Case-insensitive substring matching
- Multiple keyword matches per announcement
- Matched keywords stored in `matched_keywords` column

---

## Output Structure

### CSV Output Format

**File:** `outputs/pipe/csv/asx_pipe_announcements_YYYYMMDD_HHMMSS.csv`

**Columns:**
```csv
ticker,datetime,price_sensitive,headline,pdf_url,company_name,matched_keywords,downloaded_file_path
CBA,14/12/2025 8:30 PM,true,Capital Raising via Institutional Placement,https://...,Commonwealth Bank,"placement, capital raising, institutional placement",outputs/pipe/pdfs/CBA_Capital_Raising.pdf
NAB,15/12/2025 9:00 AM,false,Completion of Share Purchase Plan,https://...,National Australia Bank,"share purchase plan, spp",
```

**Key Fields:**
- `ticker`: ASX ticker code
- `datetime`: Announcement date/time (DD/MM/YYYY HH:MM AM/PM)
- `price_sensitive`: Whether announcement is price-sensitive
- `headline`: Announcement title
- `pdf_url`: Link to PDF document
- `company_name`: Full company name
- `matched_keywords`: Comma-separated list of matched PIPE keywords
- `downloaded_file_path`: Path to downloaded PDF (if enabled)

### Database Schema

**Table:** `asx_pipe_announcements`

```sql
CREATE TABLE asx_pipe_announcements (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(255),
    announcement_datetime TIMESTAMP,
    title TEXT,
    pdf_link TEXT,
    description TEXT,  -- Matched keywords (comma-separated)
    is_price_sensitive BOOLEAN,
    downloaded_file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_pipe_announcement UNIQUE (ticker, announcement_datetime, title)
);
```

**Idempotency:** `ON CONFLICT DO NOTHING` ensures duplicate announcements are not inserted

---

## Parameters Reference

### `output_dir`
- **Type:** `str`
- **Default:** `"./outputs/pipe"`
- **Purpose:** Base directory for all outputs
- **Subdirectories Created:**
  - `outputs/pipe/csv/` - CSV reports
  - `outputs/pipe/json/` - JSON exports
  - `outputs/pipe/pdfs/` - Downloaded PDFs

### `period`
- **Type:** `str`
- **Options:** `"today"`, `"week"`, `"month"`, `"3months"`, `"6months"`, `"all"`
- **Default:** `"week"`
- **Purpose:** Time range for announcement search
- **Recommendation:** Use `"week"` for daily scans, `"6months"` for historical analysis

### `sample_size`
- **Type:** `int`
- **Default:** `0` (all companies)
- **Purpose:** Limit number of companies scanned (for testing)
- **Values:**
  - `0`: Scan all ~2000 companies (production)
  - `50`: Quick test (30-60 seconds)
  - `100-500`: Medium test
- **Use Case:** Set to 50-100 for development/testing

### `download_pdfs`
- **Type:** `bool`
- **Default:** `False`
- **Purpose:** Whether to download announcement PDFs
- **Impact:**
  - `True`: Slower execution, requires storage, enables PDF analysis
  - `False`: Faster execution, metadata only
- **Recommendation:** Use `False` for daily metadata scans, `True` for detailed analysis

### `use_database`
- **Type:** `bool`
- **Default:** `False` (interactive), `True` (script/prefect)
- **Purpose:** Enable database persistence
- **Requirements:** Configured database service in environment
- **Behavior:** If database unavailable, logs warning and continues with file output

---

## Performance Optimization

### Execution Time Estimates

| Configuration | Companies | Period | PDFs | Estimated Time |
|---------------|-----------|--------|------|----------------|
| Full Production | 2000 | week | No | 15-20 minutes |
| Full Production | 2000 | week | Yes | 25-35 minutes |
| Quick Test | 50 | week | No | 30-60 seconds |
| Quick Test | 50 | week | Yes | 2-5 minutes |
| Historical Scan | 2000 | 6months | No | 20-30 minutes |

### Optimization Strategies

#### 1. Request Throttling
- **Default Delay:** 0.5 seconds between requests
- **Purpose:** Avoid overwhelming ASX servers
- **Configurable:** Modify `AsxScraperService(delay=0.5)`

#### 2. Sample Mode for Testing
```python
# Test with 50 companies instead of 2000
sample_size=50
```
- **Speed:** 40x faster than full scan
- **Use:** Development, parameter tuning, validation

#### 3. Metadata-Only Collection
```python
# Skip PDF downloads for faster execution
download_pdfs=False
```
- **Speed:** 30-50% faster
- **Use:** Daily metadata scans, lightweight monitoring

#### 4. Period Selection
- `"today"`: Fastest, current day only
- `"week"`: Recommended for daily scans
- `"6months"`: Use sparingly, large dataset
- `"all"`: Avoid for routine scans, historical analysis only

---

## Error Handling & Resilience

### Retry Strategy

**Task-Level Retries:**
```python
@task(retries=2, retry_delay_seconds=30)
```

**Applied To:**
- `initialize_services`: Database connection failures
- `scrape_pipe_announcements_task`: HTTP failures, timeouts

**Behavior:**
- Automatic retry on transient failures
- Exponential backoff between retries
- Logs failure details

### Graceful Degradation

#### Database Unavailable
```
WARNING | Could not initialize database service: ...
```
**Behavior:** Continue execution, save to files only

#### HTTP Errors
- **Strategy:** Skip failed company, continue with next
- **Logging:** Log warning with company ticker and error
- **Impact:** Partial results returned (doesn't fail entire flow)

#### PDF Download Failures
- **Strategy:** Log warning, mark as not downloaded
- **Impact:** Metadata still collected and saved

### Error Categories

| Error Type | Handling | Flow Impact |
|------------|----------|-------------|
| Database connection | Log warning, disable database | Continue (file output) |
| HTTP timeout (single company) | Log warning, skip company | Continue with next |
| HTTP failure (all companies) | Retry 2x, then fail flow | Flow fails |
| PDF download failure | Log warning, skip PDF | Continue (metadata saved) |
| Invalid parameters | Fail immediately | Flow fails with validation error |

---

## Monitoring & Observability

### Prefect Logging

**Log Levels:**
- `INFO`: Flow start/completion, major milestones
- `WARNING`: HTTP errors, database issues, PDF failures
- `ERROR`: Unrecoverable failures

**Key Log Messages:**
```
INFO | Starting target scrape for tickers: ...
INFO | Found 15 PIPE announcements from 50 companies
INFO | Saved CSV: outputs/pipe/csv/asx_pipe_announcements_20260111_142935.csv
WARNING | Could not initialize database service: ...
```

### Flow Return Metrics

```python
{
    "total_announcements": 15,          # Number of PIPE announcements
    "unique_companies": 12,              # Companies with announcements
    "execution_time_seconds": 45.23,     # Execution time
    "saved_files": ["path/to/file.csv"]  # Output file paths
}
```

**Access in Prefect UI:**
- Navigate to Flow Runs
- View return value in "State Details"
- Use for alerting/monitoring

### Alerting Recommendations

**Prefect Automations (Future):**
1. **Zero Results Alert**: Trigger if `total_announcements == 0` on trading days
2. **High Execution Time**: Alert if execution > 30 minutes
3. **Database Failure**: Notify infrastructure team if database unavailable

---

## Development Workflow

### Adding New Keywords

**File:** `src/services/asx_scraper/filters.py`

```python
PIPE_KEYWORDS = [
    # ... existing keywords
    'new_keyword',  # Add your keyword here
]
```

**Testing:**
```bash
# Run unit tests
uv run pytest tests/unit/asx_scraper/test_filters.py -v

# Test in notebook
marimo edit notebooks/asx/asx_pipe_scraper.py
# Enable sample mode, run with new keyword
```

### Modifying Flow Logic

**Steps:**
1. Edit `notebooks/asx/asx_pipe_scraper.py`
2. Test in interactive mode: `marimo edit notebooks/asx/asx_pipe_scraper.py`
3. Validate script mode: `python notebooks/asx/asx_pipe_scraper.py`
4. Redeploy: `prefect deploy --name asx-pipe-scraper-daily`

### Debugging

**Interactive Mode:**
1. Open notebook: `marimo edit notebooks/asx/asx_pipe_scraper.py`
2. Enable sample mode (small dataset)
3. Add debug prints in task functions
4. Use run button to execute
5. Inspect DataFrame results

**Script Mode:**
```bash
# Run with Prefect logging
python notebooks/asx/asx_pipe_scraper.py

# Check logs in terminal
# Logs include task execution, warnings, errors
```

**Prefect UI:**
1. Navigate to Flow Runs: `http://localhost:4200`
2. View flow run details
3. Check task logs, execution times
4. Review return values

---

## Common Issues & Solutions

### Issue: "No announcements found"
**Possible Causes:**
- Non-trading day (weekends, holidays)
- Period too narrow (`"today"` on quiet day)
- Network connectivity issues

**Solutions:**
- Expand period to `"week"` or `"month"`
- Check ASX website manually
- Verify internet connection

---

### Issue: "Database connection failed"
**Error:** `WARNING | Could not initialize database service: ...`

**Solutions:**
- Verify database service is running
- Check `.env` configuration
- Confirm database credentials
- **Note:** Flow continues with file output (graceful degradation)

---

### Issue: "Execution time too long"
**Symptoms:** Full scan takes > 30 minutes

**Solutions:**
- Enable sample mode for testing: `sample_size=50`
- Disable PDF downloads: `download_pdfs=False`
- Use narrower period: `"week"` instead of `"6months"`
- Check network latency

---

### Issue: "Marimo multiple definitions error"
**Error:** `Variable 'pd' is defined in multiple cells`

**Cause:** pandas imported in both `app.setup` and cell

**Solution:** Import in cell only, remove from `app.setup`
```python
@app.cell
def _():
    import marimo as mo
    import pandas as pd
    return (mo, pd)
```

---

## Best Practices

### 1. Development Cycle
```
Edit Mode → Test with Sample → Script Mode → Deploy to Prefect
```

### 2. Parameter Selection

**For Development:**
```python
period="week"
sample_size=50
download_pdfs=False
use_database=False
```

**For Production:**
```python
period="week"
sample_size=0           # All companies
download_pdfs=False     # Metadata only
use_database=True
```

**For Deep Analysis:**
```python
period="month"
sample_size=0
download_pdfs=True      # Enable PDF analysis
use_database=True
```

### 3. Scheduling
- Run after market close (6 PM AEST)
- Avoid weekends/holidays
- Use cron: `"0 18 * * 1-5"` (weekdays only)

### 4. Data Management
- Archive old CSV files periodically
- Monitor storage for PDF downloads
- Database: Set retention policy (e.g., 90 days)

---

## Related Documentation

- **ASX Announcement Scraper:** Ticker-specific announcement fetching
- **ASX Appendix 5B Scraper:** Quarterly cash flow report extraction
- **AsxScraperService API:** Full service documentation
- **Prefect + Marimo Architecture:** Unified notebook patterns

---

## API Reference

### AsxScraperService Methods (Relevant)

```python
service.scrape_pipe_announcements(
    period: str = "M6",
    download_pdfs: bool = False,
    save_to_db: bool = False,
    sample_size: Optional[int] = None
) -> pd.DataFrame
```

**Returns:** DataFrame with columns:
- `ticker`, `datetime`, `price_sensitive`, `headline`, `pdf_url`
- `company_name`, `matched_keywords`, `downloaded_file_path`

### AnnouncementFilters Methods

```python
filters.is_pipe_announcement(headline: str) -> bool
filters.get_matched_pipe_keywords(headline: str) -> List[str]
```

---

## Support & Troubleshooting

### Logs Location
- **Console:** Real-time output during execution
- **Prefect UI:** `http://localhost:4200/flow-runs`
- **File Logs:** Check Prefect server logs if enabled

### Health Checks

```bash
# Test notebook syntax
uv run python -m marimo check notebooks/asx/asx_pipe_scraper.py

# Test flow execution
uv run python notebooks/asx/asx_pipe_scraper.py

# Test imports
uv run python -c "from services.asx_scraper import AsxScraperService; print('OK')"
```

### Contact & Contributions
- Report issues with execution logs
- Provide sample data for debugging
- Test changes with sample mode first

---

## Appendix: Example Outputs

### Console Output (Script Mode)
```
14:25:40.012 | INFO | Flow run 'masterful-ladybug' - Beginning flow run
14:25:40.449 | INFO | Task run 'initialize_services-7b9' - Finished in state Completed()
14:25:40.454 | INFO | Task run 'scrape_pipe_announcements_task-5af' - Starting target scrape
14:25:47.090 | INFO | Task run 'scrape_pipe_announcements_task-5af' - Scraped 15 announcements
14:25:47.102 | INFO | Task run 'persist_results-fdc' - Saved CSV: outputs/pipe/csv/...
14:25:47.141 | INFO | Flow run 'masterful-ladybug' - Finished in state Completed()
```

### Sample CSV Data
```csv
ticker,datetime,price_sensitive,headline,pdf_url,company_name,matched_keywords
CBA,14/12/2025 8:30 PM,true,Capital Raising via Institutional Placement,https://announcements.asx.com.au/...,Commonwealth Bank,"placement,capital raising,institutional placement"
NAB,15/12/2025 9:00 AM,false,Completion of Share Purchase Plan,https://announcements.asx.com.au/...,National Australia Bank,"share purchase plan,spp"
BHP,15/12/2025 10:30 AM,true,Proposed Issue of Securities,https://announcements.asx.com.au/...,BHP Group,"issue of securities,proposed issue"
```

---

**Last Updated:** 2026-01-11  
**Version:** 1.0  
**Maintainer:** ASX Scraper Team

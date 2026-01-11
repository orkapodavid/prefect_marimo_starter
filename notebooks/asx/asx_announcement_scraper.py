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

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup:
    from prefect import task, flow
    from services.asx_scraper import AsxScraperService
    import os
    from datetime import datetime

# ============================================================
# TASKS
# ============================================================

@app.function
@task(retries=2, retry_delay_seconds=30)
def initialize_services(output_dir: str, use_database: bool):
    """Initialize ASX scraper service with optional database."""
    from prefect import get_run_logger
    logger = get_run_logger()
    
    database_service = None
    if use_database:
        try:
            from services.mssql import MSSQLService
            from shared_utils.config import get_config
            config = get_config()
            database_service = MSSQLService(
                server=config.db_server,
                database=config.db_name,
                username=config.db_user,
                password=config.db_password
            )
            logger.info("Database service initialized")
        except Exception as e:
            logger.warning(f"Could not initialize database service: {e}")
    
    service = AsxScraperService(
        output_dir=output_dir,
        database_service=database_service
    )
    
    return service

@app.function
@task(retries=2, retry_delay_seconds=30)
def scrape_target_announcements_task(service: AsxScraperService, tickers: list, period: str, download_pdfs: bool):
    """Scrape announcements for specific tickers."""
    from prefect import get_run_logger
    logger = get_run_logger()
    
    logger.info(f"Starting target scrape for {len(tickers)} tickers: {tickers}")
    
    df = service.scrape_target_announcements(
        tickers=tickers,
        period=period,
        download_pdfs=download_pdfs,
        save_to_db=service.database_service is not None
    )
    
    logger.info(f"Scraped {len(df)} announcements")
    return df

@app.function
@task
def persist_results(service: AsxScraperService, df, output_format: str):
    """Persist results to file."""
    from prefect import get_run_logger
    logger = get_run_logger()
    
    if df.empty:
        logger.info("No results to save")
        return []
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    saved_files = []
    
    if output_format in ['csv', 'both']:
        csv_path = os.path.join(service.csv_dir, f'asx_announcements_{timestamp}.csv')
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        saved_files.append(csv_path)
        logger.info(f"Saved CSV: {csv_path}")
    
    if output_format in ['json', 'both']:
        json_path = os.path.join(service.json_dir, f'asx_announcements_{timestamp}.json')
        df.to_json(json_path, orient='records', indent=2)
        saved_files.append(json_path)
        logger.info(f"Saved JSON: {json_path}")
    
    return saved_files

# ============================================================
# FLOW
# ============================================================

@app.function
@flow(name="asx-announcement-scraper", log_prints=True)
def run_announcement_scraper(
    tickers: list,
    period: str = "today",
    output_dir: str = "./outputs/announcements",
    download_pdfs: bool = False,
    output_format: str = "csv",
    use_database: bool = False
):
    """Main flow for announcement scraping by ticker."""
    import time
    start_time = time.time()
    
    # Initialize service
    service = initialize_services(output_dir, use_database)
    
    # Scrape announcements
    df = scrape_target_announcements_task(service, tickers, period, download_pdfs)
    
    # Persist results
    saved_files = persist_results(service, df, output_format)
    
    # Calculate statistics
    elapsed = time.time() - start_time
    price_sensitive_count = df['price_sensitive'].sum() if not df.empty else 0
    
    announcements_per_ticker = {}
    if not df.empty:
        announcements_per_ticker = df.groupby('ticker').size().to_dict()
    
    return {
        "total_announcements": len(df),
        "announcements_per_ticker": announcements_per_ticker,
        "price_sensitive_count": int(price_sensitive_count),
        "execution_time_seconds": round(elapsed, 2),
        "saved_files": saved_files
    }

# ============================================================
# INTERACTIVE CELLS (edit mode only)
# ============================================================

@app.cell
def _():
    import marimo as mo
    return (mo,)

@app.cell
def _(mo):
    if mo.app_meta().mode == "edit":
        ticker_input = mo.ui.text_area(
            value="CBA,NAB,BHP",
            label="Tickers (comma-separated)",
            full_width=True
        )
        
        period_selector = mo.ui.dropdown(
            options=["today", "week", "month", "3months", "6months", "all"],
            value="today",
            label="Time Period"
        )
        
        download_pdfs_toggle = mo.ui.checkbox(value=False, label="Download PDFs")
        
        format_selector = mo.ui.radio(
            options=["csv", "json", "both"],
            value="csv",
            label="Output Format"
        )
        
        use_db_toggle = mo.ui.checkbox(value=False, label="Save to Database")
        
        run_button = mo.ui.run_button(label="Run Announcement Scraper")
    return ticker_input, period_selector, download_pdfs_toggle, format_selector, use_db_toggle, run_button

@app.cell
def _(mo, ticker_input, period_selector, download_pdfs_toggle, format_selector, use_db_toggle, run_button):
    if mo.app_meta().mode == "edit":
        mo.vstack([
            mo.md("# ASX Announcement Scraper"),
            mo.md("Fetch announcements for specific tickers"),
            ticker_input,
            period_selector,
            download_pdfs_toggle,
            format_selector,
            use_db_toggle,
            run_button
        ])
    return

@app.cell
def _(mo, run_button, ticker_input, period_selector, download_pdfs_toggle, format_selector, use_db_toggle):
    result_df = None
    if mo.app_meta().mode == "edit" and run_button.value:
        tickers_list = [t.strip().upper() for t in ticker_input.value.split(',') if t.strip()]
        
        result = run_announcement_scraper(
            tickers=tickers_list,
            period=period_selector.value,
            output_dir="./outputs/announcements_test",
            download_pdfs=download_pdfs_toggle.value,
            output_format=format_selector.value,
            use_database=use_db_toggle.value
        )
        
        # Read the saved file to display
        import pandas as pd
        if result['saved_files']:
            csv_files = [f for f in result['saved_files'] if f.endswith('.csv')]
            if csv_files:
                result_df = pd.read_csv(csv_files[0])
    return result_df, tickers_list

@app.cell
def _(mo, result_df, run_button):
    if mo.app_meta().mode == "edit" and run_button.value:
        if result_df is not None and not result_df.empty:
            mo.vstack([
                mo.md(f"## Results: {len(result_df)} announcements found"),
                mo.md(f"**Price Sensitive:** {result_df['price_sensitive'].sum()}"),
                mo.ui.table(result_df.head(20), selection=None)
            ])
        else:
            mo.md("No announcements found")
    return

# ============================================================
# SCRIPT EXECUTION (production)
# ============================================================

@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        run_announcement_scraper(
            tickers=["CBA", "NAB", "BHP", "RIO", "WES"],
            period="today",
            output_dir="./outputs/watchlist",
            download_pdfs=True,
            output_format="both",
            use_database=True
        )
    return

if __name__ == "__main__":
    app.run()

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
def scrape_pipe_announcements_task(service: AsxScraperService, period: str, sample_size: int, download_pdfs: bool):
    """Scrape PIPE announcements using the service."""
    from prefect import get_run_logger
    logger = get_run_logger()
    
    logger.info(f"Starting PIPE scrape: period={period}, sample_size={sample_size}, download_pdfs={download_pdfs}")
    
    df = service.scrape_pipe_announcements(
        period=period,
        download_pdfs=download_pdfs,
        save_to_db=service.database_service is not None,
        sample_size=sample_size if sample_size > 0 else None
    )
    
    logger.info(f"Scraped {len(df)} PIPE announcements")
    return df

@app.function
@task
def persist_results(service: AsxScraperService, df, output_format: str):
    """Persist results to CSV."""
    from prefect import get_run_logger
    logger = get_run_logger()
    
    if df.empty:
        logger.info("No results to save")
        return []
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    saved_files = []
    
    if output_format in ['csv', 'both']:
        csv_path = os.path.join(service.csv_dir, f'asx_pipe_announcements_{timestamp}.csv')
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        saved_files.append(csv_path)
        logger.info(f"Saved CSV: {csv_path}")
    
    if output_format in ['json', 'both']:
        json_path = os.path.join(service.json_dir, f'asx_pipe_announcements_{timestamp}.json')
        df.to_json(json_path, orient='records', indent=2)
        saved_files.append(json_path)
        logger.info(f"Saved JSON: {json_path}")
    
    return saved_files

# ============================================================
# FLOW
# ============================================================

@app.function
@flow(name="asx-pipe-scraper", log_prints=True)
def run_pipe_scraper(
    output_dir: str = "./outputs/pipe",
    period: str = "week",
    sample_size: int = 0,
    download_pdfs: bool = False,
    use_database: bool = False
):
    """Main flow for PIPE announcements scraping."""
    import time
    start_time = time.time()
    
    # Initialize service
    service = initialize_services(output_dir, use_database)
    
    # Scrape announcements
    df = scrape_pipe_announcements_task(service, period, sample_size, download_pdfs)
    
    # Persist results
    saved_files = persist_results(service, df, output_format='csv')
    
    # Calculate statistics
    elapsed = time.time() - start_time
    
    return {
        "total_announcements": len(df),
        "unique_companies": df['ticker'].nunique() if not df.empty else 0,
        "execution_time_seconds": round(elapsed, 2),
        "saved_files": saved_files
    }

# ============================================================
# INTERACTIVE CELLS (edit mode only)
# ============================================================

@app.cell
def _():
    import marimo as mo
    import pandas as pd
    return (mo, pd)

@app.cell
def _(mo):
    if mo.app_meta().mode == "edit":
        period_selector = mo.ui.dropdown(
            options=["today", "week", "month", "3months", "6months", "all"],
            value="week",
            label="Time Period"
        )
        
        sample_toggle = mo.ui.checkbox(value=True, label="Sample Mode (testing)")
        sample_size_slider = mo.ui.slider(start=10, stop=500, step=10, value=50, label="Sample Size")
        download_pdfs_toggle = mo.ui.checkbox(value=False, label="Download PDFs")
        use_db_toggle = mo.ui.checkbox(value=False, label="Save to Database")
        
        run_button = mo.ui.run_button(label="Run PIPE Scraper")
    return period_selector, sample_toggle, sample_size_slider, download_pdfs_toggle, use_db_toggle, run_button

@app.cell
def _(mo, period_selector, sample_toggle, sample_size_slider, download_pdfs_toggle, use_db_toggle, run_button):
    if mo.app_meta().mode == "edit":
        mo.vstack([
            mo.md("# ASX PIPE Scraper"),
            mo.md("Scan ASX companies for placement/capital raising announcements"),
            period_selector,
            sample_toggle,
            mo.hstack([sample_size_slider]) if sample_toggle.value else mo.md(""),
            download_pdfs_toggle,
            use_db_toggle,
            run_button
        ])
    return

@app.cell
def _(mo, run_button, period_selector, sample_toggle, sample_size_slider, download_pdfs_toggle, use_db_toggle, pd):
    result_df = None
    if mo.app_meta().mode == "edit" and run_button.value:
        sample_size = sample_size_slider.value if sample_toggle.value else 0
        result = run_pipe_scraper(
            output_dir="./outputs/pipe_test",
            period=period_selector.value,
            sample_size=sample_size,
            download_pdfs=download_pdfs_toggle.value,
            use_database=use_db_toggle.value
        )
        
        # Read the saved CSV to display
        if result['saved_files']:
            result_df = pd.read_csv(result['saved_files'][0])
    return result_df,

@app.cell
def _(mo, result_df, run_button):
    if mo.app_meta().mode == "edit" and run_button.value:
        if result_df is not None and not result_df.empty:
            mo.vstack([
                mo.md(f"## Results: {len(result_df)} PIPE announcements found"),
                mo.md(f"**Unique Companies:** {result_df['ticker'].nunique()}"),
                mo.ui.table(result_df.head(20), selection=None)
            ])
        else:
            mo.md("No PIPE announcements found")
    return

# ============================================================
# SCRIPT EXECUTION (production)
# ============================================================

@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        run_pipe_scraper(
            output_dir="./outputs/pipe",
            period="week",
            sample_size=0,
            download_pdfs=False,
            use_database=True
        )
    return

if __name__ == "__main__":
    app.run()
    app.run()

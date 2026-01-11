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
def scrape_appendix5b_reports_task(service: AsxScraperService, download_pdfs: bool):
    """Scrape Appendix 5B reports."""
    from prefect import get_run_logger
    logger = get_run_logger()
    
    logger.info("Starting Appendix 5B scrape")
    
    summary = service.scrape_appendix5b_reports(
        download_pdfs=download_pdfs,
        save_to_db=service.database_service is not None
    )
    
    logger.info(f"Found {summary.total_announcements_found} Appendix 5B reports")
    return summary

@app.function
@task
def persist_summary(service: AsxScraperService, summary):
    """Persist summary to JSON."""
    from prefect import get_run_logger
    logger = get_run_logger()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_path = os.path.join(service.output_dir, f'summary_{timestamp}.json')
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary.model_dump_json(indent=2))
    
    logger.info(f"Saved summary: {summary_path}")
    return summary_path

# ============================================================
# FLOW
# ============================================================

@app.function
@flow(name="asx-appendix5b-scraper", log_prints=True)
def run_appendix5b_scraper(
    output_dir: str = "./outputs/appendix5b",
    download_pdfs: bool = True,
    use_database: bool = False
):
    """Main flow for Appendix 5B scraping."""
    import time
    start_time = time.time()
    
    # Initialize service
    service = initialize_services(output_dir, use_database)
    
    # Scrape reports
    summary = scrape_appendix5b_reports_task(service, download_pdfs)
    
    # Persist summary
    summary_path = persist_summary(service, summary)
    
    # Calculate statistics
    elapsed = time.time() - start_time
    success_rate = (summary.successful_extractions / summary.total_announcements_found * 100) if summary.total_announcements_found > 0 else 0
    
    return {
        "total_reports": summary.total_announcements_found,
        "successful_extractions": summary.successful_extractions,
        "extraction_success_rate": round(success_rate, 1),
        "warnings_count": summary.warnings_count,
        "execution_time_seconds": round(elapsed, 2),
        "summary_file": summary_path
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
        download_pdfs_toggle = mo.ui.checkbox(value=True, label="Download PDFs (required for extraction)")
        use_db_toggle = mo.ui.checkbox(value=False, label="Save to Database")
        run_button = mo.ui.run_button(label="Run Appendix 5B Scraper")
    return download_pdfs_toggle, use_db_toggle, run_button

@app.cell
def _(mo, download_pdfs_toggle, use_db_toggle, run_button):
    if mo.app_meta().mode == "edit":
        mo.vstack([
            mo.md("# ASX Appendix 5B Scraper"),
            mo.md("Scrape today's Appendix 5B and Quarterly Activities reports"),
            download_pdfs_toggle,
            use_db_toggle,
            run_button
        ])
    return

@app.cell
def _(mo, run_button, download_pdfs_toggle, use_db_toggle):
    summary_result = None
    if mo.app_meta().mode == "edit" and run_button.value:
        result = run_appendix5b_scraper(
            output_dir="./outputs/appendix5b_test",
            download_pdfs=download_pdfs_toggle.value,
            use_database=use_db_toggle.value
        )
        summary_result = result
    return summary_result,

@app.cell
def _(mo, summary_result, run_button):
    if mo.app_meta().mode == "edit" and run_button.value and summary_result:
        # Read summary file to get details
        import json
        with open(summary_result['summary_file'], 'r') as f:
            summary_data = json.load(f)
        
        # Create results DataFrame
        import pandas as pd
        results_df = pd.DataFrame([
            {
                'Ticker': r['stock_code'],
                'Headline': r['headline'],
                'Total Funding ($A\'000)': r['section_8_data']['item_8_6_total_available_funding'],
                'Est. Quarters': r['section_8_data']['item_8_7_estimated_quarters'],
                'Extraction Success': r['extraction_success'],
                'Warning': r['warning']
            }
            for r in summary_data['results']
        ])
        
        mo.vstack([
            mo.md(f"## Results: {summary_result['total_reports']} reports found"),
            mo.md(f"**Successful Extractions:** {summary_result['successful_extractions']} ({summary_result['extraction_success_rate']}%)"),
            mo.md(f"**Warnings:** {summary_result['warnings_count']}"),
            mo.ui.table(results_df, selection=None)
        ])
    return results_df,

# ============================================================
# SCRIPT EXECUTION (production)
# ============================================================

@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        run_appendix5b_scraper(
            output_dir="./outputs/appendix5b",
            download_pdfs=True,
            use_database=True
        )
    return

if __name__ == "__main__":
    app.run()

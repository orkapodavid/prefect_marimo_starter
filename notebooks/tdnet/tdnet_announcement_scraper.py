# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.10.9",
#     "prefect>=3.0.0",
#     "pandas>=2.0.0",
#     "beautifulsoup4>=4.12.0",
#     "requests>=2.31.0",
#     "pydantic>=2.0.0",
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup:
    from prefect import task, flow
    from datetime import date, datetime, timedelta
    import os

# ============================================================
# TASKS
# ============================================================


@app.function
@task(retries=2, retry_delay_seconds=30)
def initialize_scraper(language: str, delay: float = 1.0, timeout: int = 30, max_retries: int = 3):
    """Initialize TDnet scraper with language and configuration."""
    from prefect import get_run_logger
    from services.tdnet.tdnet_announcement_scraper import TdnetAnnouncementScraper
    from services.tdnet.tdnet_announcement_models import TdnetLanguage

    logger = get_run_logger()

    lang_enum = TdnetLanguage.JAPANESE if language.lower() == "japanese" else TdnetLanguage.ENGLISH

    scraper = TdnetAnnouncementScraper(
        language=lang_enum, delay=delay, timeout=timeout, max_retries=max_retries
    )

    logger.info(f"Initialized TDnet scraper for {lang_enum.value}")
    return scraper


@app.function
@task
def resolve_date_range(
    period: str = "today", start_date: str | None = None, end_date: str | None = None
) -> tuple[date, date]:
    """Resolve date range from period or explicit dates.

    Args:
        period: One of 'today', 'week', 'month'
        start_date: Explicit start date (YYYY-MM-DD), overrides period
        end_date: Explicit end date (YYYY-MM-DD), overrides period

    Returns:
        Tuple of (start_date, end_date)
    """
    from prefect import get_run_logger

    logger = get_run_logger()

    # Explicit dates take precedence
    if start_date and end_date:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        logger.info(f"Using explicit date range: {start} to {end}")
        return start, end

    # Period-based resolution
    today = date.today()

    if period == "today":
        start, end = today, today
    elif period == "week":
        start = today - timedelta(days=7)
        end = today
    elif period == "month":
        start = today - timedelta(days=30)
        end = today
    else:
        raise ValueError(f"Unknown period: {period}. Use 'today', 'week', or 'month'")

    logger.info(f"Resolved period '{period}' to date range: {start} to {end}")
    return start, end


@app.function
@task(retries=2, retry_delay_seconds=60)
def scrape_and_persist(
    scraper,
    start_date: date,
    end_date: date,
    query: str = "",
    output_dir: str = "./data/output/tdnet_announcements",
    output_format: str = "csv",
) -> dict:
    """Execute the scraping operation and persist results.

    Combined into single task to avoid Prefect serialization issues with
    TdnetScrapeResult (which implements __iter__).
    """
    from prefect import get_run_logger

    logger = get_run_logger()

    logger.info(f"Starting scrape from {start_date} to {end_date}")

    try:
        result = scraper.scrape(start_date, end_date, query)
        logger.info(f"Scraped {len(result)} announcements across {result.page_count} pages")

        # Persist results immediately
        saved_files = []

        if len(result) == 0:
            logger.info("No announcements to save")
        else:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Generate filename with date and language
            today_str = datetime.now().strftime("%Y_%m_%d")
            language = result.language.value

            df = result.to_dataframe()

            if output_format in ["csv", "both"]:
                csv_filename = f"{today_str}_{language}.csv"
                csv_path = os.path.join(output_dir, csv_filename)
                df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                saved_files.append(csv_path)
                logger.info(f"Saved CSV: {csv_path}")

            if output_format in ["json", "both"]:
                json_filename = f"{today_str}_{language}.json"
                json_path = os.path.join(output_dir, json_filename)
                df.to_json(json_path, orient="records", indent=2, force_ascii=False)
                saved_files.append(json_path)
                logger.info(f"Saved JSON: {json_path}")

        # Return simple dict (no complex objects that Prefect might iterate)
        return {
            "total_count": len(result),
            "page_count": result.page_count,
            "language": result.language.value,
            "saved_files": saved_files,
        }
    finally:
        scraper.close()


# ============================================================
# FLOW
# ============================================================


@app.function
@flow(name="tdnet-announcement-scraper", log_prints=True)
def run_tdnet_scraper(
    language: str = "english",
    period: str = "today",
    start_date: str | None = None,
    end_date: str | None = None,
    query: str = "",
    delay: float = 1.0,
    output_dir: str = "./data/output/tdnet_announcements",
    output_format: str = "csv",
):
    """Main flow for TDnet announcement scraping.

    Args:
        language: 'english' or 'japanese'
        period: 'today', 'week', or 'month' (ignored if start_date/end_date provided)
        start_date: Explicit start date (YYYY-MM-DD)
        end_date: Explicit end date (YYYY-MM-DD)
        query: Search query (English only)
        delay: Seconds between requests
        output_dir: Output directory for CSV/JSON files
        output_format: 'csv', 'json', or 'both'

    Returns:
        Dict with scrape statistics
    """
    import time

    start_time = time.time()

    # Initialize scraper
    scraper = initialize_scraper(language, delay)

    # Resolve date range
    resolved_start, resolved_end = resolve_date_range(period, start_date, end_date)

    # Scrape and persist in one task (avoids Prefect serialization issues)
    scrape_result = scrape_and_persist(
        scraper, resolved_start, resolved_end, query, output_dir, output_format
    )

    # Calculate statistics
    elapsed = time.time() - start_time

    return {
        "language": language,
        "start_date": str(resolved_start),
        "end_date": str(resolved_end),
        "total_announcements": scrape_result["total_count"],
        "page_count": scrape_result["page_count"],
        "execution_time_seconds": round(elapsed, 2),
        "saved_files": scrape_result["saved_files"],
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
        language_selector = mo.ui.dropdown(
            options=["english", "japanese"], value="english", label="Language"
        )

        period_selector = mo.ui.dropdown(
            options=["today", "week", "month"], value="today", label="Period"
        )

        query_input = mo.ui.text(value="", label="Search Query (English only)", full_width=True)

        delay_slider = mo.ui.slider(
            start=0.5, stop=3.0, step=0.5, value=1.0, label="Delay (seconds)"
        )

        format_selector = mo.ui.radio(
            options=["csv", "json", "both"], value="csv", label="Output Format"
        )

        run_button = mo.ui.run_button(label="Run TDnet Scraper")
    return (
        language_selector,
        period_selector,
        query_input,
        delay_slider,
        format_selector,
        run_button,
    )


@app.cell
def _(
    mo, language_selector, period_selector, query_input, delay_slider, format_selector, run_button
):
    if mo.app_meta().mode == "edit":
        mo.vstack(
            [
                mo.md("# TDnet Announcement Scraper"),
                mo.md("Fetch company announcements from TDnet (English or Japanese)"),
                language_selector,
                period_selector,
                query_input,
                delay_slider,
                format_selector,
                run_button,
            ]
        )
    return


@app.cell
def _(
    mo, run_button, language_selector, period_selector, query_input, delay_slider, format_selector
):
    result_data = None
    if mo.app_meta().mode == "edit" and run_button.value:
        result_data = run_tdnet_scraper(
            language=language_selector.value,
            period=period_selector.value,
            query=query_input.value,
            delay=delay_slider.value,
            output_dir="./data/output/tdnet_announcements",
            output_format=format_selector.value,
        )
    return (result_data,)


@app.cell
def _(mo, result_data, run_button):
    if mo.app_meta().mode == "edit" and run_button.value and result_data:
        mo.vstack(
            [
                mo.md("## Results"),
                mo.md(f"**Language:** {result_data['language']}"),
                mo.md(f"**Date Range:** {result_data['start_date']} to {result_data['end_date']}"),
                mo.md(f"**Announcements:** {result_data['total_announcements']}"),
                mo.md(f"**Pages Scraped:** {result_data['page_count']}"),
                mo.md(f"**Execution Time:** {result_data['execution_time_seconds']}s"),
                mo.md(
                    f"**Saved Files:** {', '.join(result_data['saved_files']) if result_data['saved_files'] else 'None'}"
                ),
            ]
        )
    return


# ============================================================
# SCRIPT EXECUTION (production)
# ============================================================


@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        # Default production run - today's English announcements
        run_tdnet_scraper(
            language="english",
            period="today",
            output_dir="./data/output/tdnet_announcements",
            output_format="csv",
        )
    return


if __name__ == "__main__":
    app.run()

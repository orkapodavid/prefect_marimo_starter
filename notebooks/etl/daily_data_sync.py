import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup:
    from prefect import task, flow
    import polars as pl
    from pathlib import Path
    from src.shared_utils.prefect_notifications import notify_on_failure

# ============================================================
# TASKS - Reusable units of work
# ============================================================


@app.function
@task(retries=2, retry_delay_seconds=30)
def extract_from_source(source_path: str) -> pl.DataFrame:
    """Extract data from source file or database."""
    print(f"Extracting from: {source_path}")

    if source_path.endswith(".parquet"):
        return pl.read_parquet(source_path)
    elif source_path.endswith(".csv"):
        return pl.read_csv(source_path)
    else:
        # Fallback for demo purposes if file doesn't exist
        print(f"File {source_path} not found, generating sample data")
        return pl.DataFrame(
            {
                "id": range(1, 11),
                "value": [x * 10 for x in range(1, 11)],
                "timestamp": ["2023-01-01"] * 10,
            }
        )


@app.function
@task
def validate_data(df: pl.DataFrame) -> pl.DataFrame:
    """Validate data quality."""
    initial_count = len(df)

    # Remove nulls in critical columns if they exist
    if "id" in df.columns:
        df = df.drop_nulls(subset=["id"])

    # Remove duplicates
    if "id" in df.columns:
        df = df.unique(subset=["id"])

    final_count = len(df)
    print(
        f"Validation: {initial_count} -> {final_count} rows ({initial_count - final_count} removed)"
    )

    return df


@app.function
@task
def transform_data(df: pl.DataFrame) -> pl.DataFrame:
    """Apply business transformations."""
    # Example transformation
    if "timestamp" in df.columns:
        df = df.with_columns(
            [pl.col("timestamp").str.strptime(pl.Datetime, format="%Y-%m-%d", strict=False)]
        )
    return df


@app.function
@task(retries=3, retry_delay_seconds=60)
def load_to_destination(df: pl.DataFrame, dest_path: str) -> dict:
    """Load data to destination."""
    print(f"Loading {len(df)} rows to: {dest_path}")

    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest_path)

    return {"rows_loaded": len(df), "destination": dest_path}




# ============================================================
# FLOW - Main pipeline orchestration
# ============================================================


@app.function
@flow(name="daily-data-sync", log_prints=True, on_failure=[notify_on_failure])
def run_daily_sync(
    source: str = "data/input/daily.parquet",
    destination: str = "data/output/synced.parquet",
    environment: str = "dev",
) -> dict:
    """
    Daily data synchronization pipeline.

    Args:
        source: Path to source data
        destination: Path to write output
        environment: Runtime environment (dev/staging/prod)

    Returns:
        Summary dict with processing stats
    """
    print(f"Starting daily sync in {environment} environment")

    # Extract
    df = extract_from_source(source)

    # Transform
    df = validate_data(df)
    df = transform_data(df)

    # Load
    result = load_to_destination(df, destination)

    print(f"Pipeline complete: {result}")
    return result


# ============================================================
# INTERACTIVE CELLS - Development & Debugging (edit mode only)
# ============================================================


@app.cell
def _():
    import marimo as mo
    import altair as alt

    return alt, mo


@app.cell
def _(mo):
    # Configuration UI for interactive testing
    source_input = mo.ui.text(value="data/sample/test.parquet", label="Source Path")
    dest_input = mo.ui.text(value="data/output/test_output.parquet", label="Destination Path")

    run_button = mo.ui.run_button(label="Test Pipeline")

    mo.vstack([source_input, dest_input, run_button])
    return dest_input, run_button, source_input


@app.cell
def _(dest_input, extract_from_source, mo, run_button, source_input, transform_data, validate_data):
    # Only execute in edit mode when button clicked
    result = None
    if mo.app_meta().mode == "edit" and run_button.value:
        try:
            # Run individual tasks for debugging
            df = extract_from_source(source_input.value)
            df = validate_data(df)
            df = transform_data(df)
            result = {"preview": df.head(10), "total_rows": len(df)}
        except Exception as e:
            result = {"error": str(e)}
    return (result,)


@app.cell
def _(mo, result):
    # Data preview (edit mode only)
    _table = None
    if mo.app_meta().mode == "edit" and result and "preview" in result:
        _table = mo.ui.table(result["preview"])
    _table
    return


# ============================================================
# SCRIPT EXECUTION - Production run (script mode only)
# ============================================================


@app.cell
def _(mo, run_daily_sync):
    import os as _os

    if mo.app_meta().mode == "script":
        # Parse command line arguments or use defaults
        # Simple argument parsing for demo
        source = "data/input/daily.parquet"
        destination = "data/output/synced.parquet"
        environment = _os.environ.get("ENVIRONMENT", "dev")

        # Run the flow
        result = run_daily_sync(source=source, destination=destination, environment=environment)

        # Explicitly print result for visibility in logs
        print(f"Flow Result: {result}")
    return


if __name__ == "__main__":
    app.run()

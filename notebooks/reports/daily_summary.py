# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "polars>=1.0.0",
#     "prefect>=3.0.0",
#     "altair>=5.0.0"
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup:
    from prefect import task, flow
    import polars as pl
    import altair as alt


@app.function
@task
def generate_summary_data() -> pl.DataFrame:
    """Generate dummy summary data."""
    return pl.DataFrame({
        "category": ["A", "B", "C", "A", "B", "C"],
        "value": [10, 20, 30, 15, 25, 35],
        "date": ["2023-01-01"] * 3 + ["2023-01-02"] * 3
    })


@app.function
@task
def create_chart(df: pl.DataFrame):
    """Create an Altair chart."""
    chart = alt.Chart(df).mark_bar().encode(
        x="date",
        y="value",
        color="category"
    )
    # in a real flow, you might save this chart or email it
    return chart.to_json()


@app.function
@flow(name="daily-summary-report", log_prints=True)
def run_report():
    print("Generating daily summary report...")
    df = generate_summary_data()
    chart_json = create_chart(df)
    print("Report generated successfully.")
    return {"status": "success", "chart": chart_json}


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        run_report()
    return




if __name__ == "__main__":
    app.run()

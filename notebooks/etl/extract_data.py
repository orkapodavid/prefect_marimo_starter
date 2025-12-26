# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "pandas", "sqlalchemy"]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")


@app.cell
def imports():
    import pandas as pd

    from workflow_utils.config import get_settings
    return get_settings, pd


@app.cell
def config(get_settings):
    """Configuration cell - receives parameters from Prefect."""
    get_settings()
    # In interactive mode, settings will use defaults
    # When run from Prefect, parameters can be passed to the run function


@app.cell
def extract_logic(pd):
    """Main extraction logic."""
    # Simulation: Extracting data from a source (CSV or SQL)
    data = {
        "id": [1, 2, 3, 4, 5],
        "name": ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"],
        "value": [10.5, 20.0, 15.2, 5.8, 30.1],
        "timestamp": pd.Timestamp.now(),
    }
    df = pd.DataFrame(data)

    result = {"status": "success", "rows_extracted": len(df), "columns": list(df.columns)}
    return df, result


@app.cell
def data_preview(df):
    df.head()


@app.function
def run(parameters: dict = None) -> dict:
    """Entry point for Prefect task execution."""
    # app.run returns (outputs, defs)
    # defs contains all variables defined in the cells
    outputs, defs = app.run()
    # We return the 'result' variable from extract_logic cell
    return defs.get("result", {"status": "unknown"})

if __name__ == "__main__":
    app.run()

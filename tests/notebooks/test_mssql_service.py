# notebooks/src/services/mssql/test_mssql_service.py
import marimo

__generated_with = "0.10.9"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import os
    import sys
    from dotenv import load_dotenv
    import pandas as pd

    # Import from installed package
    from src.services.mssql.mssql_service import MSSQLService
    from src.shared_utils.config import get_settings

    # Load environment variables
    load_dotenv()
    return MSSQLService, get_settings, load_dotenv, mo, os, pd, sys


@app.cell
def _(mo):
    mo.md(
        r"""
        # MS SQL Service Test Notebook
        """
    )
    return


@app.cell
def _(mo):
    env_selector = mo.ui.dropdown(
        options=["dev", "prod"],
        value="dev",
        label="Environment"
    )
    env_selector
    return (env_selector,)


@app.cell
def _(MSSQLService, env_selector, get_settings, mo):
    # Initialize Service
    settings = get_settings(environment=env_selector.value)

    # Determine credentials based on selection
    if env_selector.value == "dev":
        server = settings.dev_mssql_server
        database = settings.dev_mssql_database
        username = settings.dev_mssql_username
        password = settings.dev_mssql_password
    else:
        server = settings.prod_mssql_server
        database = settings.prod_mssql_database
        username = settings.prod_mssql_username
        password = settings.prod_mssql_password

    service = None
    service_status_md = mo.md("⚠️ Service not initialized")

    if server and database and username and password:
        try:
            # We wrap this in a try block because we might not have a real DB connection
            # in this test environment, but we want to instantiate the object if possible.
            # However, MSSQLService connects in __init__, so it will fail if no DB.
            # For demonstration, we will try to connect.
            service = MSSQLService(server=server, database=database, username=username, password=password)
            service_status_md = mo.md(f"✅ Service connected to `{server}/{database}`")
        except Exception as e:
            service_status_md = mo.md(f"❌ Failed to connect: {str(e)}")
    else:
         service_status_md = mo.md("⚠️ Missing credentials in configuration.")

    service_status_md
    return database, password, server, service, service_status_md, settings, username


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Execute Query from File
        """
    )
    return


@app.cell
def _(mo):
    customer_id_input = mo.ui.number(label="Customer ID", start=1, value=1)
    run_query_btn = mo.ui.run_button(label="Run Query")

    mo.hstack([customer_id_input, run_query_btn])
    return customer_id_input, run_query_btn


@app.cell
def _(customer_id_input, mo, os, run_query_btn, service):
    query_result = mo.md("")
    df = None

    if run_query_btn.value:
        if service:
            try:
                # Path relative to repo root (assuming notebook runs with cwd at repo root or handled)
                sql_file = "sql/sales/get_customer_by_id.sql"

                # Check if we are running from notebooks/src/services/mssql/
                if not os.path.exists(sql_file):
                    # Try going up levels if running from subdir
                    # We reuse the 'os' module passed from the first cell
                    # From tests/notebooks/ -> ../../
                    sql_file = "../../" + sql_file

                df = service.execute_query_from_file(
                    file_path=sql_file,
                    params={"customer_id": customer_id_input.value}
                )

                if not df.empty:
                    query_result = mo.ui.table(df)
                else:
                    query_result = mo.md("No results found.")
            except Exception as e:
                query_result = mo.md(f"❌ Error executing query: {str(e)}")
        else:
            query_result = mo.md("⚠️ Service not connected.")

    query_result
    return df, query_result, sql_file


if __name__ == "__main__":
    app.run()

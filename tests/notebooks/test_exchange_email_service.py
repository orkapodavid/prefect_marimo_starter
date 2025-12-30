import marimo

__generated_with = "0.10.9"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import os
    import sys
    from datetime import datetime, timedelta
    from dotenv import load_dotenv
    import pandas as pd

    # shared_utils and services are available via installed package
    from src.services.exchange_email.exchange_email_service import ExchangeEmailService

    # Load environment variables
    load_dotenv()
    return ExchangeEmailService, datetime, load_dotenv, mo, os, pd, sys, timedelta


@app.cell
def _(mo):
    mo.md(
        r"""
        # Exchange Service Test Notebook
        """
    )
    return


@app.cell
def _(ExchangeEmailService, mo, os):
    # Initialize Service
    username = os.getenv("EXCHANGE_USERNAME")
    password = os.getenv("EXCHANGE_PASSWORD")
    ews_url = os.getenv("EXCHANGE_EWS_URL")

    service = None
    service_status = mo.md("⚠️ Service not initialized (check .env credentials)")

    if username and password and ews_url:
        try:
            service = ExchangeEmailService(username=username, password=password, ews_url=ews_url)
            service_status = mo.md(
                "✅ Service initialized successfully connected as `{}`".format(username)
            )
        except Exception as e:
            service_status = mo.md(f"❌ Failed to initialize service: {str(e)}")
    else:
        service_status = mo.md(
            "⚠️ Missing credentials in .env file. Please check `EXCHANGE_USERNAME`, `EXCHANGE_PASSWORD`, and `EXCHANGE_EWS_URL`."
        )

    service_status
    return ews_url, password, service, service_status, username


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Fetch Emails
        """
    )
    return


@app.cell
def _(datetime, mo, timedelta):
    # UI Controls
    yesterday = datetime.now() - timedelta(days=1)

    start_time_picker = mo.ui.date(value=yesterday.date(), label="Start Date")
    subject_filter_input = mo.ui.text(label="Subject Filter (optional)")
    sender_filter_input = mo.ui.text(label="Sender Filter (optional)")
    fetch_button = mo.ui.run_button(label="Fetch Emails")

    mo.hstack([start_time_picker, subject_filter_input, sender_filter_input, fetch_button])
    return (
        fetch_button,
        sender_filter_input,
        start_time_picker,
        subject_filter_input,
        yesterday,
    )


@app.cell
def _(
    datetime,
    fetch_button,
    mo,
    pd,
    sender_filter_input,
    service,
    start_time_picker,
    subject_filter_input,
):
    # Fetch Logic
    fetch_result = mo.md("Click 'Fetch Emails' to query.")

    if fetch_button.value and service:
        # Convert date to datetime
        start_dt = datetime.combine(start_time_picker.value, datetime.min.time())

        try:
            emails = service.get_emails(
                start_time=start_dt,
                subject_filter=subject_filter_input.value if subject_filter_input.value else None,
                sender_filter=sender_filter_input.value if sender_filter_input.value else None,
            )

            if emails:
                df = pd.DataFrame(emails)
                # Just show count of attachments
                df["attachments_count"] = df["attachments"].apply(len)
                fetch_result = mo.ui.table(
                    df[["subject", "sender", "datetime_received", "attachments_count"]],
                    selection=None,
                )
            else:
                fetch_result = mo.md("No emails found matching criteria.")

        except Exception as e:
            fetch_result = mo.md(f"❌ Error fetching emails: {str(e)}")
    elif fetch_button.value and not service:
        fetch_result = mo.md("⚠️ Service not initialized, cannot fetch.")

    fetch_result
    return emails, fetch_result, start_dt


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Send Email
        """
    )
    return


@app.cell
def _(mo):
    to_input = mo.ui.text(label="To (comma separated)")
    subject_input = mo.ui.text(label="Subject")
    body_input = mo.ui.text_area(label="Body")
    send_button = mo.ui.run_button(label="Send Email")

    mo.vstack([to_input, subject_input, body_input, send_button])
    return body_input, send_button, subject_input, to_input


@app.cell
def _(body_input, mo, send_button, service, subject_input, to_input):
    send_result = mo.md("")

    if send_button.value and service:
        to_list = [t.strip() for t in to_input.value.split(",") if t.strip()]

        if to_list and subject_input.value:
            try:
                service.send_email(
                    to_recipients=to_list, subject=subject_input.value, body=body_input.value
                )
                send_result = mo.md(f"✅ Email sent to {to_list}")
            except Exception as e:
                send_result = mo.md(f"❌ Failed to send email: {str(e)}")
        else:
            send_result = mo.md("⚠️ Please provide at least one recipient and a subject.")

    send_result
    return send_result, to_list


if __name__ == "__main__":
    app.run()

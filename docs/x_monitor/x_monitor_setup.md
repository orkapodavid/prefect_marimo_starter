# X Monitor Setup

This guide covers the local macOS setup for the X monitor workflows.

## PostgreSQL

1. Install PostgreSQL with either Postgres.app or Homebrew.
2. Create the logical databases:
   - `prefect`
   - `x_monitor`
3. Point Prefect at PostgreSQL with `PREFECT_API_DATABASE_CONNECTION_URL`.
4. Point the application at PostgreSQL with `X_MONITOR_DATABASE_URL`.

## Prefect

1. Start the local Prefect server:
   ```bash
   prefect server start
   ```
2. Create the process work pool used by the X monitor deployments:
   ```bash
   prefect work-pool create --type process local-process-pool
   ```
3. Deploy the notebooks:
   ```bash
   prefect deploy --all
   ```

## Gmail Delivery

### Gmail SMTP

Gmail SMTP is the primary delivery path. Configure these settings in `.env`:

- `X_MONITOR_GMAIL_PROVIDER=gmail_smtp`
- `X_MONITOR_GMAIL_SMTP_HOST=smtp.gmail.com`
- `X_MONITOR_GMAIL_SMTP_PORT=587`
- `X_MONITOR_GMAIL_SMTP_USERNAME=<gmail address>`
- `X_MONITOR_GMAIL_SMTP_PASSWORD=<app password>`
- `X_MONITOR_GMAIL_SMTP_FROM=<gmail address>`

### Gmail API

Gmail API is the fallback provider when SMTP app passwords are unavailable.

1. Enable the Gmail API in a Google Cloud project.
2. Create an installed-app OAuth client.
3. Set `X_MONITOR_GMAIL_PROVIDER=gmail_api`.
4. Point `X_MONITOR_GMAIL_API_CREDENTIALS_FILE` and `X_MONITOR_GMAIL_API_TOKEN_FILE`
   at your local OAuth files.

### Optional ADC Path

If you want to use Application Default Credentials deliberately, run:

```bash
gcloud auth application-default login --client-id-file <oauth-client.json> --scopes=https://www.googleapis.com/auth/gmail.send
```

Then set:

- `X_MONITOR_GMAIL_API_USE_ADC=true`
- `X_MONITOR_GMAIL_PROVIDER=gmail_api`

## launchd

The repo includes `launchd` wrapper assets for macOS:

- `launchd/x_monitor_prefect_server.plist`
- `launchd/x_monitor_prefect_worker.plist`
- `scripts/macos/x_monitor_run_prefect_server.sh`
- `scripts/macos/x_monitor_run_prefect_worker.sh`

Load them with:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/x_monitor_prefect_server.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/x_monitor_prefect_worker.plist
```

## Smoke Checks

Run these after configuration:

```bash
uv run python -m services.x_monitor.x_monitor_cli sync-targets --config config/x_monitor/x_monitor_targets.yaml
uv run python -m services.x_monitor.x_monitor_cli health
uv run python -m services.x_monitor.x_monitor_cli test-email
prefect deploy --all
```

Verify the deployments appear in the Prefect UI and that the `local-process-pool`
worker is running before relying on schedules.


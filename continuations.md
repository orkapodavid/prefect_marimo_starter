# X Monitor Continuation Notes

Date: 2026-03-25

## Current Local State

These items have already been created locally:

- `.env`
- `config/x_monitor/x_monitor_targets.yaml`
- `tmp/x_account.txt.template`
- PostgreSQL databases: `x_monitor`, `prefect`
- X monitor Alembic schema migrated into `x_monitor`
- `data/x_monitor/twscrape/accounts.db` initialized

These files are local runtime files and are intentionally not committed:

- `config/x_monitor/x_monitor_targets.yaml`
- `.env`
- `tmp/x_account.txt.template`
- `data/x_monitor/twscrape/accounts.db`

## Fill-In Blanks

### 1. Gmail SMTP settings

Edit `.env` and replace these values:

- `X_MONITOR_GMAIL_SMTP_USERNAME=BLANK_FILL_YOUR_GMAIL_ADDRESS`
- `X_MONITOR_GMAIL_SMTP_PASSWORD=BLANK_FILL_YOUR_GMAIL_APP_PASSWORD`
- `X_MONITOR_GMAIL_SMTP_FROM=BLANK_FILL_YOUR_GMAIL_ADDRESS`
- `X_MONITOR_OPERATOR_EMAILS=BLANK_FILL_SAFE_TEST_RECIPIENT_EMAIL`

How to get the Gmail app password:

1. Open `https://myaccount.google.com/security`
2. Turn on 2-Step Verification if it is not already enabled
3. Open `https://myaccount.google.com/apppasswords`
4. Create an app password
5. Paste the 16-character password into `X_MONITOR_GMAIL_SMTP_PASSWORD`

If the App Passwords page is unavailable, switch to the Gmail API path instead of SMTP.

### 2. X monitor recipients

Edit `config/x_monitor/x_monitor_targets.yaml` and replace every
`BLANK_FILL_SAFE_TEST_RECIPIENT_EMAIL` with your safe test inbox.

### 3. X account credentials template

Edit `tmp/x_account.txt.template` and replace the single line with:

`your_x_username:your_x_password:your_email@example.com:manual_code_only`

Keep the final field as `manual_code_only`.

## Important Note About Prefect

Do not put `PREFECT_API_DATABASE_CONNECTION_URL` into `.env`.
This repo's Pydantic settings loader rejects unknown keys in `.env`.

When Prefect needs the database URL later, use one of these approaches instead:

- inline env var:
  `PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://localhost:5432/prefect uv run prefect server start`
- or `prefect config set PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://localhost:5432/prefect`

## Remaining Runtime Gaps

At the time this note was written:

- X monitor DB health: working
- twscrape DB file: exists, but no authenticated X account added yet
- Prefect server: not running
- Gmail test: not run yet because credentials are still blank

## Next Actions For The Agent

After the user fills the blanks and says they are ready:

1. Run `uv run python -m services.x_monitor.x_monitor_cli test-email`
2. Add the X account to twscrape:
   `uv run twscrape --db data/x_monitor/twscrape/accounts.db add_accounts tmp/x_account.txt.template username:password:email:email_password`
3. Run manual X login:
   `uv run twscrape --db data/x_monitor/twscrape/accounts.db login_accounts --manual`
4. Ask the user for the one-time verification code if X requests it
5. Verify the account list:
   `uv run twscrape --db data/x_monitor/twscrape/accounts.db accounts`
6. Continue with real end-to-end review and testing


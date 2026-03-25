# X/Twitter Account Monitor — PostgreSQL + Prefect + Gmail + macOS

## 1. Objective

Build a self-hosted X/Twitter account monitor that:

- watches a configured set of X accounts for new posts
- optionally includes replies
- filters by keywords, regexes, media, and repost/retweet rules
- sends immediate email alerts and daily digest emails through Gmail
- stores all state in a local PostgreSQL instance
- uses Prefect (Python SDK + local Prefect server) for scheduling and observability
- runs on a single macOS machine with no paid X API dependency

The system should be production-minded for a single-machine deployment:

- restart-safe
- idempotent
- no duplicate alerts
- explicit failure logging
- simple to operate locally

---

## 2. Chosen Architecture

### 2.1 Primary components

1. **Collector:** `twscrape`
2. **Application database:** local PostgreSQL
3. **Scheduler/orchestrator:** self-hosted Prefect server + Prefect Python flows/deployments
4. **Email delivery:** Gmail SMTP by default, Gmail API fallback when SMTP app-password auth is unavailable
5. **Host OS:** macOS
6. **Service manager:** `launchd`

### 2.2 Deployment topology on one Mac

Processes/services:

1. **PostgreSQL**
   - one local PostgreSQL server instance
   - preferably managed by Postgres.app or Homebrew/PostgreSQL package tooling

2. **Prefect server**
   - local API/UI
   - backed by PostgreSQL, not SQLite

3. **Monitor serve process**
   - Python process that registers/serves multiple Prefect deployments
   - stays running and listens for scheduled runs

4. **Flow subprocesses**
   - spawned by Prefect when scheduled runs execute

### 2.3 Database split recommendation

Use one PostgreSQL cluster with **two logical databases**:

- `prefect` — for Prefect orchestration metadata
- `x_monitor` — for application state and business tables

This is preferred over sharing the same DB/schema for both because:

- it isolates migrations
- it reduces accidental coupling
- it makes backup/restore easier
- it avoids collisions between Prefect’s internal schema and app tables

---

## 3. Why this design

### 3.1 Why `flow.serve` instead of work pools/workers

For a single always-on Mac, use Prefect’s **local-process serving model** instead of the more complex work-pool/worker setup.

That means:

- define flows in Python
- create deployments in Python
- serve them from a long-lived Python process
- let Prefect schedule and execute flow runs in subprocesses on the same machine

This is simpler than introducing process work pools and a separate worker unless there is a later need for more machines or heterogeneous infrastructure.

### 3.2 Why Gmail SMTP first

For a single-machine alerting tool, Gmail SMTP is the simplest path:

- low implementation complexity
- easy to test manually
- works well for low-volume operational alerts

However, some Google accounts cannot use app passwords. Therefore the implementation must support a **second transport**:

- `gmail_api`

The app should expose a provider interface so either transport can be used without changing higher-level alert logic.

### 3.3 Why PostgreSQL everywhere

PostgreSQL is the local source of truth for:

- monitor targets
- rules
- watermarks
- seen posts
- match history
- notification attempts
- run history
- health snapshots

Using PostgreSQL instead of SQLite improves:

- concurrency behavior
- query flexibility
- transactional safety
- future path to remote deployment

---

## 4. Repo Layout

```text
x-monitor/
  pyproject.toml
  README.md
  .env.example
  config.example.yml
  alembic.ini
  migrations/
  src/x_monitor/
    __init__.py
    settings.py
    logging.py
    db.py
    models.py
    repositories/
      targets.py
      posts.py
      notifications.py
      runs.py
    collectors/
      twscrape_client.py
      normalization.py
      matching.py
    notifications/
      base.py
      gmail_smtp.py
      gmail_api.py
      formatter.py
    flows/
      poll_accounts.py
      send_digest.py
      healthcheck.py
      serve.py
    services/
      polling.py
      digest.py
      health.py
      bootstrap.py
    cli.py
  scripts/
    init_postgres.sql
    create_launchd_plists.py
    run_prefect_server.sh
    run_prefect_serve.sh
  launchd/
    com.example.prefect-server.plist
    com.example.xmonitor-serve.plist
  tests/
    test_matching.py
    test_dedup.py
    test_digest.py
    test_notifications.py
    test_polling.py
```

---

## 5. Python / Package Stack

Target:

- Python 3.12 preferred

Suggested dependencies:

- `prefect`
- `sqlalchemy`
- `psycopg[binary]`
- `alembic`
- `pydantic`
- `pydantic-settings`
- `PyYAML`
- `jinja2`
- `twscrape`
- `httpx`
- `tenacity`
- `email-validator`
- `google-api-python-client` (only for Gmail API fallback)
- `google-auth`
- `google-auth-oauthlib`
- `structlog` or standard `logging`
- `pytest`
- `pytest-asyncio`
- `freezegun`

Notes:

- use SQLAlchemy ORM or SQLAlchemy Core; either is acceptable, but the schema and migrations must be explicit
- use `psycopg` for PostgreSQL connections
- keep Gmail transport behind a small interface so SMTP and API implementations are swappable

---

## 6. Configuration Model

Use **two config layers**:

1. `.env` for secrets and host-specific environment
2. `config.yml` for targets, schedules, and rule behavior

### 6.1 `.env` example

```dotenv
APP_ENV=production
TZ=Asia/Singapore
LOG_LEVEL=INFO

APP_DATABASE_URL=postgresql+psycopg://x_monitor:x_monitor@localhost:5432/x_monitor
PREFECT_API_URL=http://127.0.0.1:4200/api
PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://prefect:prefect@localhost:5432/prefect

# Gmail SMTP primary path
EMAIL_PROVIDER=gmail_smtp
GMAIL_SMTP_HOST=smtp.gmail.com
GMAIL_SMTP_PORT=587
GMAIL_SMTP_USERNAME=alerts@example@gmail.com
GMAIL_SMTP_PASSWORD=your_16_char_app_password
GMAIL_SMTP_FROM=alerts@example@gmail.com
GMAIL_SMTP_USE_STARTTLS=true

# Gmail API fallback
GMAIL_API_CREDENTIALS_FILE=/Users/you/.config/x-monitor/google-oauth-client.json
GMAIL_API_TOKEN_FILE=/Users/you/.config/x-monitor/google-token.json
GMAIL_API_FROM=alerts@example@gmail.com

# twscrape account database
TWSCRAPE_ACCOUNTS_DB=/Users/you/.local/share/x-monitor/twscrape_accounts.db
```

### 6.2 `config.yml` example

```yaml
app:
  timezone: Asia/Singapore
  poll_batch_limit_per_target: 25
  default_poll_window_minutes: 15
  digest_window: daily
  operator_emails:
    - ops@example.com

schedules:
  poll_cron: "*/5 * * * *"
  digest_cron: "0 8 * * *"
  health_cron: "*/30 * * * *"

notifications:
  immediate_alerts_enabled: true
  daily_digest_enabled: true
  subject_prefix: "[X Monitor]"

monitoring:
  targets:
    - username: some_account
      include_replies: false
      include_retweets: false
      media_only: false
      keywords_any: ["earnings", "guidance", "launch"]
      keywords_all: []
      regex_any: []
      alert_recipients: ["alerts@example.com"]
      digest_recipients: ["digest@example.com"]
      active: true

    - username: another_account
      include_replies: true
      include_retweets: false
      media_only: true
      keywords_any: []
      keywords_all: []
      regex_any:
        - "\\bpartnership\\b"
        - "\\bSEC\\b"
      alert_recipients: ["alerts@example.com"]
      digest_recipients: ["digest@example.com"]
      active: true
```

### 6.3 Settings precedence

1. environment variables
2. `.env`
3. YAML config
4. code defaults

---

## 7. PostgreSQL Schema

Use Alembic migrations from day one.

### 7.1 Required tables

#### `targets`

- `id` UUID PK
- `username` text unique not null
- `user_id` text null
- `include_replies` boolean not null default false
- `include_retweets` boolean not null default false
- `media_only` boolean not null default false
- `keywords_any` jsonb not null default `[]`
- `keywords_all` jsonb not null default `[]`
- `regex_any` jsonb not null default `[]`
- `alert_recipients` jsonb not null default `[]`
- `digest_recipients` jsonb not null default `[]`
- `active` boolean not null default true
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

Indexes:

- unique index on `username`
- partial index on active targets if desired

#### `target_watermarks`

- `target_id` UUID PK/FK
- `last_seen_post_id` text null
- `last_seen_post_time` timestamptz null
- `last_successful_poll_at` timestamptz null
- `last_attempted_poll_at` timestamptz null
- `consecutive_failures` integer not null default 0
- `last_error` text null

#### `posts`

- `id` UUID PK
- `post_id` text unique not null
- `target_id` UUID FK not null
- `author_username` text not null
- `author_user_id` text null
- `created_at` timestamptz not null
- `text_raw` text not null
- `text_normalized` text not null
- `url` text not null
- `is_reply` boolean not null default false
- `is_retweet` boolean not null default false
- `has_media` boolean not null default false
- `lang` text null
- `raw_json` jsonb not null
- `inserted_at` timestamptz not null

Indexes:

- unique index on `post_id`
- index on `(target_id, created_at desc)`
- index on `created_at desc`

#### `post_matches`

- `id` UUID PK
- `post_id` UUID FK not null
- `target_id` UUID FK not null
- `matched` boolean not null
- `matched_rules` jsonb not null default `[]`
- `match_reason` text null
- `created_at` timestamptz not null

Indexes:

- index on `(target_id, created_at desc)`
- unique optional index on `post_id` if one match record per ingested post

#### `notification_events`

- `id` UUID PK
- `post_id` UUID FK null
- `target_id` UUID FK null
- `kind` text not null   # immediate_alert | digest | operator_alert
- `provider` text not null   # gmail_smtp | gmail_api
- `recipient` text not null
- `subject` text not null
- `status` text not null   # pending | sent | failed | skipped
- `attempt_count` integer not null default 0
- `last_attempt_at` timestamptz null
- `sent_at` timestamptz null
- `error_message` text null
- `payload_json` jsonb not null
- `idempotency_key` text unique not null
- `created_at` timestamptz not null

#### `flow_runs_app`

Application-level run tracking, distinct from Prefect’s own metadata.

- `id` UUID PK
- `flow_name` text not null
- `prefect_flow_run_id` text null
- `started_at` timestamptz not null
- `finished_at` timestamptz null
- `status` text not null
- `counts_json` jsonb not null default `{}`
- `error_message` text null

#### `digest_bookmarks`

- `digest_key` text PK   # e.g. daily:2026-03-24:alerts@example.com
- `window_start` timestamptz not null
- `window_end` timestamptz not null
- `sent_at` timestamptz not null
- `recipient` text not null

#### `operator_events`

- `id` UUID PK
- `event_type` text not null
- `severity` text not null
- `message` text not null
- `details_json` jsonb not null default `{}`
- `created_at` timestamptz not null
- `dedupe_key` text null

---

## 8. Twscrape Integration

### 8.1 Collector strategy

Use `twscrape` for all X/Twitter collection.

Required capabilities used by the app:

- `user_by_login(username)` to resolve user ID
- `user_tweets(user_id, limit=N)` for posts-only mode
- `user_tweets_and_replies(user_id, limit=N)` when replies are enabled

Optional future capability:

- `list_timeline(list_id, limit=N)` if the operator later wants list-based monitoring

### 8.2 Account auth strategy

Preferred:

- import cookie-authenticated accounts into the twscrape account DB

Fallback:

- username/password login with email verification

The implementation must **not** couple email-alert Gmail credentials to twscrape verification credentials. Keep these separate.

### 8.3 Rate-limit strategy

Because twscrape/X limits can vary, the polling service must:

- keep per-run poll sizes modest
- stop scanning once it reaches the stored watermark
- avoid deep backfills during normal polling
- expose soft degradation when rate-limited
- not advance the watermark on failure

### 8.4 Bootstrap strategy

When adding a target for the first time:

- resolve `user_id`
- fetch latest posts
- set watermark to the newest seen post
- by default **do not alert on historical posts**

Provide an optional `--backfill` mode for explicit historical ingestion.

---

## 9. Matching Rules

### 9.1 Rule pipeline

For each newly ingested post, evaluate in this order:

1. reject if retweet/repost and `include_retweets=false`
2. reject if reply and `include_replies=false`
3. reject if `media_only=true` and no media exists
4. normalize text
5. if `keywords_any` is non-empty, require at least one keyword hit
6. if `keywords_all` is non-empty, require all keyword hits
7. if `regex_any` is non-empty, require at least one regex hit
8. if no rule lists are defined, treat every new post as a match

### 9.2 Normalization rules

Normalize for matching only, while preserving raw text separately:

- lowercase
- Unicode normalize (NFKC)
- collapse repeated whitespace
- strip zero-width/control chars when safe
- optionally expand URLs only if already present in parsed text metadata

Do **not** mutate the original rendered text used in the email body.

### 9.3 Match recording

Record a `post_matches` row even for non-matches if the post was newly seen. This improves auditability.

---

## 10. Notification Architecture

Implement a small provider abstraction:

```python
class EmailProvider(Protocol):
    def send_email(
        self,
        *,
        to: list[str],
        subject: str,
        text_body: str,
        html_body: str | None,
        reply_to: str | None = None,
    ) -> SendResult: ...
```

### 10.1 Provider implementations

#### A. `gmail_smtp`

Use Python `smtplib` with either:

- port 587 + STARTTLS
- or port 465 + implicit SSL

Default to **587 + STARTTLS**.

#### B. `gmail_api`

Fallback implementation using Google OAuth 2.0 and Gmail API `users.messages.send`.

### 10.2 Provider selection rules

1. default provider from config/env
2. if SMTP auth fails with a configuration/auth-class error and `gmail_api` is configured, surface a clear operator message recommending switch/fallback
3. do not silently switch transports without logging

### 10.3 Email templates

Use Jinja2 templates.

Templates:

- `immediate_alert.txt.j2`
- `immediate_alert.html.j2`
- `digest.txt.j2`
- `digest.html.j2`
- `operator_alert.txt.j2`

### 10.4 Immediate alert content

Subject example:

```text
[X Monitor] @username matched: earnings
```

Body should include:

- account handle
- post timestamp
- post URL
- full rendered text
- flags: reply / retweet / media
- matched rule details
- ingestion timestamp

### 10.5 Digest content

Digest groups should be:

1. by recipient
2. by account
3. then ordered newest-first

Include:

- digest time window
- counts per account
- matched rule summary
- one card/section per post
- links to original X posts

### 10.6 Idempotency

Immediate alerts:

- idempotency key = `immediate:{recipient}:{post_id}`

Digests:

- idempotency key = `digest:{recipient}:{window_start}:{window_end}`

If a matching notification event already has `sent` status, skip sending.

---

## 11. Gmail-specific Implementation Rules

### 11.1 SMTP mode (primary)

Implement with:

- host: `smtp.gmail.com`
- port: `587`
- STARTTLS
- username: full Gmail address
- password: app password

### 11.2 Gmail API fallback mode

Used when:

- app passwords are unavailable
- organizational policy blocks SMTP app-password auth
- the operator prefers OAuth-managed sending

Implementation notes:

- use installed-app OAuth flow
- persist token JSON securely in the user config directory
- send MIME messages through Gmail API
- keep the same templating and idempotency logic as SMTP mode

### 11.3 Quota-aware behavior

The monitor should assume Gmail is **low-to-moderate-volume only**.

Therefore:

- dedupe aggressively
- prefer daily digests for noisy targets
- optionally batch multiple immediate matches within a short interval in a future enhancement
- alert the operator when send failures suggest quota or rate-limit issues

---

## 12. Prefect Design

### 12.1 Prefect server

Use a self-hosted Prefect server backed by PostgreSQL.

The app should expect:

- `PREFECT_API_URL=http://127.0.0.1:4200/api`
- Prefect server process running continuously

### 12.2 Flows

Implement three flows.

#### `poll_accounts_flow()`

Purpose:

- poll all active targets
- ingest unseen posts
- evaluate matching rules
- queue/send immediate alerts
- update watermarks

Runs:

- every 5 minutes by default

#### `send_digest_flow()`

Purpose:

- build digest window
- query matched posts not yet included in that recipient’s digest window
- send one digest email per recipient
- persist bookmark/send record

Runs:

- daily at 08:00 local time by default

#### `healthcheck_flow()`

Purpose:

- verify DB connectivity
- verify Prefect config
- verify twscrape accounts exist and are usable
- optionally perform a Gmail connectivity smoke test without actually sending to external users
- emit operator alert on repeated failures

Runs:

- every 30 minutes by default

### 12.3 Tasks inside flows

Break each flow into Prefect tasks where it helps with retrying and logging:

For polling:

- `load_active_targets()`
- `resolve_missing_user_ids()`
- `fetch_recent_posts(target)`
- `store_posts(posts)`
- `evaluate_matches(target, posts)`
- `send_immediate_alerts(match_batch)`
- `update_watermark(target, newest_post)`
- `record_run_summary()`

For digests:

- `load_digest_recipients()`
- `collect_digest_items(recipient, window)`
- `render_digest(recipient, items)`
- `send_digest_email()`
- `mark_digest_sent()`

### 12.4 Retry policy

Use conservative retries:

- transient DB/network/email steps: retry 2–3 times with exponential backoff
- matching/rendering logic: usually no retry
- collector auth/rate-limit errors: retry lightly, then fail visibly

### 12.5 Serving multiple flows

Use a single long-lived serve process that serves all deployments together.

Pattern:

- `poll_accounts_flow.to_deployment(...)`
- `send_digest_flow.to_deployment(...)`
- `healthcheck_flow.to_deployment(...)`
- `prefect.serve(...)`

### 12.6 Schedule behavior

When using `serve`, set:

- `pause_on_shutdown=False`

This prevents schedules from being auto-paused when the serve process restarts.

### 12.7 Concurrency

For initial implementation:

- one serve process
- per-target fetches can be sequential or lightly concurrent
- do not over-parallelize twscrape calls until behavior is stable

Optional later:

- submit per-target work as tasks with bounded concurrency

---

## 13. Application Logic

### 13.1 Poll run algorithm

For each active target:

1. load target and watermark
2. ensure `user_id` exists, else resolve it from username
3. fetch latest posts using the correct twscrape method
4. sort newest-first if needed
5. stop iterating once `last_seen_post_id` is reached
6. stage newly unseen posts
7. insert posts transactionally with upsert on `post_id`
8. evaluate matching rules for newly inserted posts
9. create `notification_events` rows for matches
10. send immediate notifications (or mark pending for retry flow, if you choose asynchronous send semantics later)
11. update watermark to the newest successfully processed post
12. record success/failure counts

### 13.2 Transaction boundaries

Recommended boundaries:

- **transaction A**: insert posts + match records + pending notification rows
- **outside transaction**: send email(s)
- **transaction B**: mark notification rows sent/failed and update watermark

Alternative acceptable pattern:

- watermark update only after notification rows are durably persisted

Never lose new-post state because a send fails.

### 13.3 Failure semantics

If email send fails:

- keep post and match rows
- keep notification row with `failed`
- do not duplicate a second notification row for the same idempotency key
- allow retry on next run or dedicated retry logic

If target fetch fails:

- increment `consecutive_failures`
- keep prior watermark
- continue to other targets

---

## 14. macOS Deployment Plan

### 14.1 PostgreSQL on macOS

Prefer one of:

1. **Postgres.app** for easiest local setup
2. Homebrew PostgreSQL for CLI-oriented operators

### 14.2 Create databases

Example SQL:

```sql
CREATE ROLE prefect WITH LOGIN PASSWORD 'prefect';
CREATE ROLE x_monitor WITH LOGIN PASSWORD 'x_monitor';

CREATE DATABASE prefect OWNER prefect;
CREATE DATABASE x_monitor OWNER x_monitor;
```

### 14.3 Initialize app schema

Run:

```bash
alembic upgrade head
```

### 14.4 Start local Prefect server

Environment:

```bash
export PREFECT_API_DATABASE_CONNECTION_URL='postgresql+asyncpg://prefect:prefect@localhost:5432/prefect'
export PREFECT_API_URL='http://127.0.0.1:4200/api'
```

Run:

```bash
prefect server start
```

### 14.5 Serve the flows

Run the application serve entrypoint:

```bash
python -m x_monitor.flows.serve
```

This process should:

- register/update deployments
- keep monitoring for scheduled runs
- remain running under `launchd`

---

## 15. `launchd` Service Layout

Use `launchd` because it is the native macOS service manager.

Create **two LaunchAgents** for a single-user deployment:

1. `com.example.prefect-server`
2. `com.example.xmonitor-serve`

Use `~/Library/LaunchAgents` for per-user startup.

### 15.1 Wrapper scripts

Do not place long complex shell commands directly in the plist. Use wrapper scripts.

#### `scripts/run_prefect_server.sh`

Responsibilities:

- `cd` into repo
- activate virtualenv
- export Prefect env vars
- start `prefect server start`

#### `scripts/run_prefect_serve.sh`

Responsibilities:

- `cd` into repo
- activate virtualenv
- export app env vars
- run `python -m x_monitor.flows.serve`

### 15.2 Example LaunchAgent: Prefect server

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.example.prefect-server</string>

    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>/Users/you/projects/x-monitor/scripts/run_prefect_server.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/you/Library/Logs/x-monitor-prefect-server.out.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/you/Library/Logs/x-monitor-prefect-server.err.log</string>
  </dict>
</plist>
```

### 15.3 Example LaunchAgent: monitor serve process

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.example.xmonitor-serve</string>

    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>/Users/you/projects/x-monitor/scripts/run_prefect_serve.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/you/Library/Logs/x-monitor-serve.out.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/you/Library/Logs/x-monitor-serve.err.log</string>
  </dict>
</plist>
```

### 15.4 Load commands

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.prefect-server.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.xmonitor-serve.plist
```

For updates during development, `bootout` then `bootstrap` again.

---

## 16. CLI Requirements

Provide a CLI with at least these commands:

```text
x-monitor init-db
x-monitor migrate
x-monitor sync-targets --config config.yml
x-monitor import-cookies --cookies-file cookies.json --username monitor_account
x-monitor test-email
x-monitor bootstrap-targets
x-monitor backfill --username some_account --limit 100
x-monitor prefect-serve
x-monitor health
```

### 16.1 Command behavior

- `init-db` — create roles/DBs only if the agent is instructed to automate local setup; otherwise just verify connectivity
- `migrate` — run Alembic migrations
- `sync-targets` — reconcile YAML targets into DB
- `import-cookies` — seed twscrape account store
- `test-email` — send one test email to configured operator recipient
- `bootstrap-targets` — resolve user IDs and set initial watermarks
- `backfill` — explicit historical ingestion without changing normal polling assumptions
- `prefect-serve` — local entrypoint used by launchd wrapper
- `health` — connectivity and status report

---

## 17. Logging and Observability

### 17.1 Logs

Every log line should include:

- timestamp
- level
- component
- target username when applicable
- flow name / run ID when inside a Prefect run
- notification recipient when applicable

### 17.2 Metrics to record per run

- active target count
- targets succeeded
- targets failed
- posts fetched
- new posts inserted
- matches found
- emails sent
- emails failed
- total duration

### 17.3 Operator alerts

Send an operator alert when:

- Gmail auth fails repeatedly
- Prefect server is unreachable
- PostgreSQL is unreachable
- twscrape has no usable accounts
- a target fails N consecutive times (default 3)

Use a dedupe window so the same operator failure does not spam repeatedly.

---

## 18. Security Requirements

- never commit `.env` or OAuth tokens
- keep file permissions restricted
- keep Gmail alert credentials separate from twscrape verification credentials
- redact secrets from logs
- redact cookie values from logs and exceptions
- avoid embedding passwords in launchd plist files; prefer wrapper scripts sourcing a `.env`

Optional enhancement:

- support reading secrets from macOS Keychain later

---

## 19. Testing Requirements

### 19.1 Unit tests

Must cover:

- keyword matching
- regex matching
- media-only filtering
- reply and retweet filtering
- normalization behavior
- idempotency-key generation
- digest grouping

### 19.2 Integration tests

Must cover:

- insert same post twice => no duplicate post row
- same matched post twice => no duplicate immediate notification send
- failed email send => notification row marked failed, watermark not corrupted
- successful digest => digest bookmark stored
- restart serve process => schedules remain active

### 19.3 Smoke tests for manual verification on macOS

1. PostgreSQL reachable
2. Prefect server UI opens
3. `x-monitor test-email` succeeds
4. `x-monitor bootstrap-targets` resolves all configured usernames
5. one target posts something new
6. next polling run captures it exactly once
7. email received once
8. digest contains the item once

---

## 20. Acceptance Criteria

The implementation is acceptable only if it demonstrates all of the following:

1. local PostgreSQL is used for both Prefect backend and application state
2. Prefect schedules are created from Python and visible in the local Prefect UI
3. monitor runs survive process restarts via launchd
4. new matching posts trigger exactly one immediate email alert per recipient
5. daily digests are delivered exactly once per recipient/window
6. duplicate runs do not duplicate alerts
7. Gmail SMTP works with a personal Gmail account configured via app password
8. Gmail API fallback path exists and is documented
9. all migrations are reproducible from a clean machine
10. macOS setup instructions are complete enough to reproduce end-to-end locally

---

## 21. Implementation Notes for Another LLM Agent

### 21.1 Strong guidance

- prefer **simple local-process Prefect serving** over work pools/workers
- use **two local PostgreSQL databases**: `prefect` and `x_monitor`
- implement **SMTP first**, but include a provider abstraction and a **Gmail API fallback**
- use `launchd` for process supervision on macOS
- make **polling idempotent** and **notification sends deduplicated**
- do not optimize for scale before correctness
- do not introduce Redis, Celery, Docker, or Kubernetes into the first version

### 21.2 Things to avoid

- do not use SQLite anywhere in the final architecture
- do not depend on the official paid X API
- do not send historical posts on first bootstrap unless explicitly requested
- do not update watermarks before durable DB writes succeed
- do not hardcode credentials into source files or plists

---

## 22. Copy-paste Prompt for Another LLM

```text
Implement a self-hosted macOS X/Twitter account monitor in Python with this exact architecture:

- Collector: twscrape
- Application database: local PostgreSQL
- Scheduler/orchestrator: self-hosted Prefect server using PostgreSQL backend
- Scheduling style: Prefect Python flows served from a long-lived local process using flow.to_deployment(...) + prefect.serve(...)
- Email delivery: Gmail SMTP first, Gmail API fallback
- Service supervision: macOS launchd

Functional requirements:
- Monitor multiple X accounts by username
- Per-target options: include_replies, include_retweets, media_only, keywords_any, keywords_all, regex_any
- Immediate email alerts for matches
- Daily digest emails
- No duplicate alerts
- Restart-safe
- Persist all monitor state in PostgreSQL
- Persist notification attempts and statuses in PostgreSQL
- Do not use SQLite
- Do not use the official paid X API

Implementation requirements:
- Python 3.12
- SQLAlchemy + Alembic + psycopg
- Prefect 3 local server
- Jinja2 email templates
- CLI commands: migrate, sync-targets, import-cookies, test-email, bootstrap-targets, backfill, prefect-serve, health
- launchd wrapper scripts and plist files included
- config.example.yml and .env.example included
- tests included for dedupe, matching, digest, and notification failure handling

Operational requirements:
- one PostgreSQL cluster with two databases: prefect and x_monitor
- Prefect server configured via PREFECT_API_DATABASE_CONNECTION_URL
- App DB configured via APP_DATABASE_URL
- schedules created in Python, not only manually in UI
- use pause_on_shutdown=False in serving logic
- keep secrets out of source control

Deliverables:
- complete runnable codebase
- migrations
- README with macOS setup steps
- sample launchd plists
- Gmail SMTP setup instructions
- Gmail API fallback setup instructions
- tests
```


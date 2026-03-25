# X Monitor Implementation Prompt — Codex CLI

> **Hand this entire file to Codex CLI as a single prompt. Do not stop until the full test suite passes, ruff is clean, marimo check passes, and every manual smoke check that can be automated has been verified.**

---

## Your mission

Implement a self-hosted X/Twitter account monitor inside the existing `prefect_marimo_starter` repository. The monitor watches X accounts for new posts, filters by keyword/regex/media rules, sends immediate Gmail alerts and daily digests, and stores all state in PostgreSQL. It runs as Prefect flows inside Marimo notebooks on a single macOS machine.

You have two reference documents in this repo:

1. **Spec**: `docs/specs/x_monitor_prefect_postgres_gmail_macos_spec.md` — the authoritative feature specification.
2. **Implementation plan**: `plans/2026-03-24-x-monitor-prefect-postgres-gmail-macos-implementation-plan.md` — the task-by-task build plan adapted to this repo's conventions.

**Read both files in full before writing any code.** The plan takes precedence over the spec when they conflict (the plan adapts the spec to this repo's architecture).

---

## Critical repo conventions (violating these is a build failure)

These conventions are enforced by the repo and MUST be followed exactly:

### 1. Notebook decorator stacking
```python
# ✅ CORRECT — @app.function wraps @task/@flow
@app.function
@task(retries=2, retry_delay_seconds=30)
def my_task():
    ...

# ❌ WRONG — Prefect decorator first
@task
@app.function
def my_task():
    ...
```

### 2. Notebook structure
Every notebook must follow this exact structure:
```python
# /// script
# requires-python = ">=3.12"
# dependencies = [...]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup:
    # ALL shared imports here
    from prefect import task, flow
    from services.x_monitor.x_monitor_foo import bar
    from shared_utils.config import get_settings
    from shared_utils.prefect_notifications import notify_on_failure

# ============================================================
# TASKS
# ============================================================

@app.function
@task(retries=2, retry_delay_seconds=30)
def my_task(): ...

# ============================================================
# FLOW
# ============================================================

@app.function
@flow(name="x-monitor-...", log_prints=True, on_failure=[notify_on_failure])
def run_x_monitor_...(config_path: str = "...", environment: str = "dev") -> dict: ...

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
        # widgets here
        pass
    return

# ============================================================
# SCRIPT EXECUTION (production)
# ============================================================

@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        result = run_x_monitor_...()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return

if __name__ == "__main__":
    app.run()
```

### 3. Import strategy
- **NEVER** use `sys.path.append()`.
- Import from installed packages: `from services.x_monitor.x_monitor_foo import bar`
- Import shared utils: `from shared_utils.config import get_settings`
- The project is installed in editable mode via `uv pip install -e .`

### 4. File naming
- Service modules: `x_monitor_<name>.py` (e.g., `x_monitor_matching.py`)
- Tests: `test_x_monitor_<name>.py`
- All files in `src/services/x_monitor/` must be prefixed with `x_monitor_`

### 5. Database naming
- Tables: `tblXMonitorTargets` (tbl + CamelCase)
- Indexes: `idxTblXMonitorTargetsUsername` (idx + tbl + CamelCase)
- NEVER use bare names like `targets` or `posts`

### 6. Config pattern
Follow the `ir_monitor` pattern exactly:
- Pydantic models for config (`XMonitorConfig`, `XMonitorRuntime`, `XMonitorDefaults`, `XMonitorTarget`)
- YAML config at `config/x_monitor/x_monitor_targets.yaml`
- Top-level shape: `runtime`, `defaults`, `targets`
- Defaults merged onto every target by the loader
- Unique target ID validation via model_validator
- Settings in `src/shared_utils/config.py` for env-var-driven values

### 7. Testing
- Unit tests ONLY — no integration tests, no live network tests
- Mock all external dependencies (twscrape, Gmail, PostgreSQL)
- Use `in_memory_x_monitor_engine` fixture with SQLite for DB tests
- Use `pytest-mock` and `unittest.mock` for mocking
- Test file location: `tests/unit/x_monitor/`

### 8. Prefect deployments
- Defined in `prefect.yaml`, NOT via `flow.serve()`
- Entrypoint format: `notebooks/x_monitor/x_monitor_poll_accounts.py:run_x_monitor_poll_accounts`
- Work pool: `local-process-pool` (process type)
- Schedules via YAML anchors

---

## Execution protocol

### For each task (1 through 12):

1. **Read the task** from the implementation plan.
2. **Write the failing test first** — create the test file with all test functions specified in the plan. Run it and confirm it fails.
3. **Write the minimal implementation** — create/modify only the files listed in the task. Follow the plan's design guidance exactly.
4. **Run the test** — confirm it passes.
5. **Run ruff** — `uv run ruff check` on all changed files. Fix any issues.
6. **Commit** — stage only the files listed, commit with the message specified.
7. **Move to the next task.**

### After all 12 tasks:

Run the full verification sequence:

```bash
# 1. All x_monitor unit tests
uv run pytest tests/unit/x_monitor -v

# 2. Config tests (ensure no regression)
uv run pytest tests/unit/test_config.py -v

# 3. Lint
uv run ruff check src/services/x_monitor src/shared_utils/config.py notebooks/x_monitor tests/unit/x_monitor

# 4. Marimo notebook validation
uv run marimo check notebooks/x_monitor/x_monitor_poll_accounts.py notebooks/x_monitor/x_monitor_send_digest.py notebooks/x_monitor/x_monitor_healthcheck.py
```

If ANY of these fail, fix the issue and re-run. Do not stop until all pass.

### Local smoke tests (run these manually after automated checks pass):

```bash
# Start Prefect server (in separate terminal)
prefect server start

# Create work pool if needed
prefect work-pool create --type process local-process-pool

# Sync targets
uv run python -m services.x_monitor.x_monitor_cli sync-targets --config config/x_monitor/x_monitor_targets.example.yaml

# Health check
uv run python -m services.x_monitor.x_monitor_cli health

# Deploy all
prefect deploy --all

# Verify deployments exist in UI at http://localhost:4200
```

---

## File inventory

Create or modify EXACTLY these files (nothing more, nothing less unless absolutely required to fix a test):

### New files to create:

```
config/x_monitor/x_monitor_targets.example.yaml

docs/x_monitor/x_monitor_setup.md

launchd/x_monitor_prefect_server.plist
launchd/x_monitor_prefect_worker.plist

migrations/x_monitor/env.py
migrations/x_monitor/script.py.mako
migrations/x_monitor/versions/<timestamp>_create_x_monitor_schema.py

notebooks/x_monitor/x_monitor_poll_accounts.py
notebooks/x_monitor/x_monitor_send_digest.py
notebooks/x_monitor/x_monitor_healthcheck.py

scripts/macos/x_monitor_run_prefect_server.sh
scripts/macos/x_monitor_run_prefect_worker.sh

src/services/x_monitor/__init__.py
src/services/x_monitor/x_monitor_bootstrap.py
src/services/x_monitor/x_monitor_cli.py
src/services/x_monitor/x_monitor_config_loader.py
src/services/x_monitor/x_monitor_database.py
src/services/x_monitor/x_monitor_digest.py
src/services/x_monitor/x_monitor_gmail_api.py
src/services/x_monitor/x_monitor_gmail_smtp.py
src/services/x_monitor/x_monitor_matching.py
src/services/x_monitor/x_monitor_models.py
src/services/x_monitor/x_monitor_notifications.py
src/services/x_monitor/x_monitor_polling.py
src/services/x_monitor/x_monitor_tables.py
src/services/x_monitor/x_monitor_targets_sync.py
src/services/x_monitor/x_monitor_text_normalizer.py
src/services/x_monitor/x_monitor_twscrape_client.py
src/services/x_monitor/templates/digest.html.j2
src/services/x_monitor/templates/digest.txt.j2
src/services/x_monitor/templates/immediate_alert.html.j2
src/services/x_monitor/templates/immediate_alert.txt.j2
src/services/x_monitor/templates/operator_alert.txt.j2

tests/unit/x_monitor/__init__.py
tests/unit/x_monitor/conftest.py
tests/unit/x_monitor/test_x_monitor_cli.py
tests/unit/x_monitor/test_x_monitor_config_loader.py
tests/unit/x_monitor/test_x_monitor_deployment_docs.py
tests/unit/x_monitor/test_x_monitor_digest.py
tests/unit/x_monitor/test_x_monitor_gmail_api.py
tests/unit/x_monitor/test_x_monitor_gmail_smtp.py
tests/unit/x_monitor/test_x_monitor_matching.py
tests/unit/x_monitor/test_x_monitor_notebook_contract.py
tests/unit/x_monitor/test_x_monitor_notifications.py
tests/unit/x_monitor/test_x_monitor_polling.py
tests/unit/x_monitor/test_x_monitor_settings.py
tests/unit/x_monitor/test_x_monitor_tables.py
tests/unit/x_monitor/test_x_monitor_targets_sync.py
tests/unit/x_monitor/test_x_monitor_text_normalizer.py
tests/unit/x_monitor/test_x_monitor_twscrape_client.py
```

### Existing files to modify:

```
alembic.ini (create if not exists, or modify if exists for other migrations)
pyproject.toml
.env.example
src/shared_utils/config.py
prefect.yaml
README.md
docs/ADDING_FLOWS.md
```

---

## Key technical details

### PostgreSQL schema (8 tables)

All tables use UUID primary keys, timestamptz for timestamps, and JSON for array/object columns.

1. **tblXMonitorTargets** — username (unique), user_id, include_replies, include_retweets, media_only, keywords_any/all (JSON), regex_any (JSON), alert_recipients (JSON), digest_recipients (JSON), active, created_at, updated_at
2. **tblXMonitorTargetWatermarks** — target_id (PK/FK), last_seen_post_id, last_seen_post_time, last_successful_poll_at, last_attempted_poll_at, consecutive_failures, last_error
3. **tblXMonitorPosts** — post_id (unique), target_id (FK), author_username, author_user_id, created_at, text_raw, text_normalized, url, is_reply, is_retweet, has_media, lang, raw_json (JSON), inserted_at
4. **tblXMonitorPostMatches** — post_id (FK), target_id (FK), matched, matched_rules (JSON), match_reason, created_at
5. **tblXMonitorNotificationEvents** — post_id (FK null), target_id (FK null), kind, provider, recipient, subject, status, attempt_count, last_attempt_at, sent_at, error_message, payload_json (JSON), idempotency_key (unique), created_at
6. **tblXMonitorFlowRuns** — flow_name, prefect_flow_run_id, started_at, finished_at, status, counts_json (JSON), error_message
7. **tblXMonitorDigestBookmarks** — digest_key (text PK), window_start, window_end, sent_at, recipient
8. **tblXMonitorOperatorEvents** — event_type, severity, message, details_json (JSON), created_at, dedupe_key

### Matching rule pipeline (evaluate in this order)

1. Reject if retweet and `include_retweets=false`
2. Reject if reply and `include_replies=false`
3. Reject if `media_only=true` and no media
4. Normalize text (lowercase, NFKC, collapse whitespace, strip zero-width)
5. If `keywords_any` non-empty → require at least one hit
6. If `keywords_all` non-empty → require all hits
7. If `regex_any` non-empty → require at least one hit
8. If no rule lists defined → treat as match

### Notification idempotency

- Immediate: `immediate:{recipient}:{post_id}`
- Digest: `digest:{recipient}:{window_start}:{window_end}`
- Skip send if matching key already has `sent` status

### Transaction boundaries (poll run)

- **TX A**: insert posts + match records + pending notification rows
- **Outside TX**: send email(s)
- **TX B**: mark notification rows sent/failed + update watermark
- Never lose post state because a send fails

### Gmail providers

1. **SMTP** (primary): `smtplib.SMTP` → `smtp.gmail.com:587` + STARTTLS + app password
2. **Gmail API** (fallback): Google OAuth installed-app flow OR explicit ADC opt-in via `google.auth.default()`
3. Never silently switch transports. Log clearly.

### Twscrape integration

- `user_by_login(username)` → resolve user_id
- `user_tweets(user_id, limit)` → posts-only
- `user_tweets_and_replies(user_id, limit)` → with replies
- Bootstrap: resolve user_id, fetch latest, set watermark to newest, do NOT alert on historical
- Rate limit: keep poll sizes modest, stop at watermark, no deep backfills

---

## Settings to add to `src/shared_utils/config.py`

Add these fields to the `Settings` class:

```python
# X Monitor
x_monitor_database_url: str = Field(default="postgresql://localhost:5432/x_monitor")
x_monitor_config_path: Path = Field(default=Path("./config/x_monitor/x_monitor_targets.yaml"))
x_monitor_workspace_dir: Path = Field(default=Path("./data/x_monitor"))
x_monitor_twscrape_accounts_db: Path = Field(default=Path("./data/x_monitor/twscrape/accounts.db"))
x_monitor_gmail_provider: str = Field(default="gmail_smtp")
x_monitor_gmail_smtp_host: str = Field(default="smtp.gmail.com")
x_monitor_gmail_smtp_port: int = Field(default=587)
x_monitor_gmail_smtp_username: str = Field(default="")
x_monitor_gmail_smtp_password: str = Field(default="")
x_monitor_gmail_smtp_from: str = Field(default="")
x_monitor_gmail_smtp_use_starttls: bool = Field(default=True)
x_monitor_gmail_api_credentials_file: str = Field(default="")
x_monitor_gmail_api_token_file: str = Field(default="")
x_monitor_gmail_api_from: str = Field(default="")
x_monitor_gmail_api_use_adc: bool = Field(default=False)
x_monitor_poll_cron: str = Field(default="*/5 * * * *")
x_monitor_digest_cron: str = Field(default="0 8 * * *")
x_monitor_health_cron: str = Field(default="*/30 * * * *")
x_monitor_timezone: str = Field(default="Asia/Singapore")
x_monitor_poll_batch_limit: int = Field(default=25)
x_monitor_immediate_alerts_enabled: bool = Field(default=True)
x_monitor_daily_digest_enabled: bool = Field(default=True)
x_monitor_subject_prefix: str = Field(default="[X Monitor]")
x_monitor_operator_emails: str = Field(default="")
x_monitor_consecutive_failure_threshold: int = Field(default=3)
```

---

## Dependencies to add to `pyproject.toml`

Add to the `dependencies` list:

```
"alembic>=1.13.0",
"jinja2>=3.1.0",
"twscrape>=0.12.0",
"tenacity>=8.2.0",
"google-api-python-client>=2.100.0",
"google-auth>=2.23.0",
"google-auth-oauthlib>=1.1.0",
"email-validator>=2.1.0",
```

Add to `dev` optional dependencies:

```
"pytest-asyncio>=0.23.0",
"freezegun>=1.4.0",
```

---

## Example YAML config (`config/x_monitor/x_monitor_targets.example.yaml`)

```yaml
runtime:
  timezone: Asia/Singapore
  poll_batch_limit: 25
  poll_window_minutes: 15
  immediate_alerts_enabled: true
  daily_digest_enabled: true
  subject_prefix: "[X Monitor]"

defaults:
  include_replies: false
  include_retweets: false
  media_only: false

targets:
  - id: openai_posts
    username: openai
    keywords_any: ["launch", "GPT", "o1", "API"]
    keywords_all: []
    regex_any: []
    alert_recipients: ["alerts@example.com"]
    digest_recipients: ["digest@example.com"]
    active: true

  - id: nvidia_ir
    username: nvidia
    include_replies: false
    include_retweets: false
    media_only: false
    keywords_any: ["earnings", "guidance", "revenue"]
    keywords_all: []
    regex_any:
      - "\\bSEC\\b"
      - "\\bpartnership\\b"
    alert_recipients: ["alerts@example.com"]
    digest_recipients: ["digest@example.com"]
    active: true
```

---

## prefect.yaml additions

Add these YAML anchors under `definitions`:

```yaml
  work_pools:
    macos_pool: &macos_pool
      name: local-process-pool
      work_queue_name: default

  schedules:
    every_5_min_singapore: &every_5_min_singapore
      cron: "*/5 * * * *"
      timezone: "Asia/Singapore"
    daily_8am_singapore: &daily_8am_singapore
      cron: "0 8 * * *"
      timezone: "Asia/Singapore"
    every_30_min_singapore: &every_30_min_singapore
      cron: "*/30 * * * *"
      timezone: "Asia/Singapore"
```

Add these deployments:

```yaml
  - name: x-monitor-poll-accounts-prod
    entrypoint: notebooks/x_monitor/x_monitor_poll_accounts.py:run_x_monitor_poll_accounts
    description: "Poll X/Twitter accounts for new posts and send immediate alerts"
    tags: [prod, x_monitor, polling]
    parameters:
      config_path: "./config/x_monitor/x_monitor_targets.yaml"
      environment: "prod"
    work_pool: *macos_pool
    schedules:
      - *every_5_min_singapore

  - name: x-monitor-send-digest-prod
    entrypoint: notebooks/x_monitor/x_monitor_send_digest.py:run_x_monitor_send_digest
    description: "Send daily digest emails for X monitor matches"
    tags: [prod, x_monitor, digest]
    parameters:
      config_path: "./config/x_monitor/x_monitor_targets.yaml"
      environment: "prod"
    work_pool: *macos_pool
    schedules:
      - *daily_8am_singapore

  - name: x-monitor-healthcheck-prod
    entrypoint: notebooks/x_monitor/x_monitor_healthcheck.py:run_x_monitor_healthcheck
    description: "Health check for X monitor infrastructure"
    tags: [prod, x_monitor, health]
    parameters:
      config_path: "./config/x_monitor/x_monitor_targets.yaml"
      environment: "prod"
    work_pool: *macos_pool
    schedules:
      - *every_30_min_singapore
```

---

## Stopping criteria

You are DONE when ALL of the following are true:

1. `uv run pytest tests/unit/x_monitor -v` — **ALL PASS**
2. `uv run pytest tests/unit/test_config.py -v` — **ALL PASS**
3. `uv run ruff check src/services/x_monitor src/shared_utils/config.py notebooks/x_monitor tests/unit/x_monitor` — **CLEAN (no errors)**
4. `uv run marimo check notebooks/x_monitor/x_monitor_poll_accounts.py notebooks/x_monitor/x_monitor_send_digest.py notebooks/x_monitor/x_monitor_healthcheck.py` — **ALL PASS**
5. All 12 tasks committed with the specified commit messages
6. The file inventory matches exactly (all files created, all modifications made)

Do NOT stop if any check fails. Fix the issue and re-run.

---

## Reference files to read before starting

Read these files in full to understand the repo's patterns:

1. `AGENTS.md` — Critical conventions
2. `docs/ADDING_FLOWS.md` — How to add flows
3. `src/shared_utils/config.py` — Settings model
4. `src/services/ir_monitor/ir_monitor_models.py` — Config model pattern
5. `src/services/ir_monitor/ir_monitor_config_loader.py` — Loader pattern
6. `notebooks/ir/ir_webchanges_monitor.py` — Complete notebook example
7. `tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py` — Contract test pattern
8. `tests/unit/ir_monitor/test_ir_monitor_settings.py` — Settings test pattern
9. `tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py` — Deployment test pattern
10. `prefect.yaml` — Deployment configuration
11. `pyproject.toml` — Dependencies and project config
12. `.env.example` — Environment variables
13. `docs/specs/x_monitor_prefect_postgres_gmail_macos_spec.md` — Full spec
14. `plans/2026-03-24-x-monitor-prefect-postgres-gmail-macos-implementation-plan.md` — Implementation plan

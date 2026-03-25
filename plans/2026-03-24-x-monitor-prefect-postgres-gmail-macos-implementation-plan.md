# X Monitor Repo-Native Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a repository-native X/Twitter account monitor that runs as Prefect + Marimo notebook flows, stores monitor state in PostgreSQL, and sends immediate Gmail alerts plus daily digests from a single macOS machine.

**Architecture:** Reuse this repository's notebook-first pattern instead of the standalone `x-monitor/` layout from the source spec. Keep Prefect flow entrypoints in notebooks under `notebooks/x_monitor/`, move reusable config, database, collection, matching, and notification logic into `src/services/x_monitor/`, register deployments directly in `prefect.yaml`, and run them via a local Prefect server plus a macOS process worker. Gmail sending should support SMTP first and Gmail API second, with the Gmail API provider able to use either explicit OAuth files or optional ADC so the user's existing `gcloud` setup can be reused deliberately.

**Tech Stack:** Python 3.12, Prefect 3, Marimo, PostgreSQL, SQLAlchemy, Alembic, twscrape, Jinja2, google-api-python-client, google-auth, google-auth-oauthlib, pytest, ruff

---

## Repo-specific customization summary

The source spec assumes a new standalone app with `flow.serve(...)`, a long-lived serve process, and a separate `x-monitor/` package layout. This repository has a different contract:

1. Flows must live inside Marimo notebooks and use `@app.function` before `@task` or `@flow`.
2. Deployments should point directly to notebook entrypoints in `prefect.yaml`.
3. The current repo uses Prefect work pools and workers, so the macOS deployment should use a local process worker instead of introducing a parallel `serve.py` architecture.
4. The repo's test strategy is unit-test-first. Do not add live network integration tests; replace those with unit tests plus documented manual smoke checks.
5. The repo's naming conventions require `x_monitor_*` module names, `tblCamelCase` table names, and `idxCamelCase` index names.
6. Repo-local durable paths should live under `config/x_monitor/`, `data/x_monitor/`, and `launchd/` rather than a separate top-level app directory.

## Setup to complete before implementation

These are the only advance items worth doing before code is written:

1. PostgreSQL on macOS
   - Install either Postgres.app or Homebrew PostgreSQL.
   - Create two logical databases: `prefect` for Prefect metadata and `x_monitor` for app state.
   - Enable `pg_trgm` in the `prefect` database before starting Prefect migrations.

2. Prefect local runtime
   - Confirm `prefect server start` works on this Mac.
   - Create a process work pool: `local-process-pool`.
   - This pool is cross-platform and future-proof.

3. Gmail delivery choice
   - Preferred path: Gmail SMTP with a dedicated sender account that has 2-Step Verification and an app password.
   - Fallback path: Gmail API with a Google Cloud project that has Gmail API enabled and a desktop OAuth client.
   - Your existing `gcloud` installation is useful, but `gcloud auth login` alone is not enough for Gmail API code. If we support ADC, the implementation should treat it as an explicit opt-in path, not an implicit assumption.

4. Gmail API auth preparation if you want the ADC path
   - Run `gcloud auth application-default login` instead of relying on normal `gcloud` login.
   - If you want Gmail scopes through ADC, create a desktop OAuth client and use it with `gcloud auth application-default login --client-id-file ... --scopes=https://www.googleapis.com/auth/gmail.send`.
   - Calendar access is not required for this feature and should stay out of scope.

5. X collection prerequisites
   - Acquire at least one usable authenticated twscrape account or cookie import path.
   - Keep X/twscrape credentials separate from Gmail credentials.
   - Decide where the durable twscrape account DB should live, preferably under `data/x_monitor/twscrape/`.

6. Local repo bootstrap
   - Ensure `.env` exists from `.env.example`.
   - Run `uv sync --extra dev` and `uv pip install -e .`.

## Decisions (resolved)

1. **Work pool naming** — `local-process-pool` for cross-platform consistency.
2. **Gmail transport default** — SMTP first, Gmail API second. ADC only when explicitly enabled.
3. **Application database isolation** — Separate `x_monitor` database from the app `workflow_app` database.
4. **Notebook split** — Three notebooks, one per flow. Each independently deployable.

## Planned file layout

```text
config/
  x_monitor/
    x_monitor_targets.example.yaml

docs/
  x_monitor/
    x_monitor_setup.md

launchd/
  x_monitor_prefect_server.plist
  x_monitor_prefect_worker.plist

migrations/
  x_monitor/
    env.py
    script.py.mako
    versions/
      <timestamp>_create_x_monitor_schema.py

notebooks/
  x_monitor/
    x_monitor_poll_accounts.py
    x_monitor_send_digest.py
    x_monitor_healthcheck.py

scripts/
  macos/
    x_monitor_run_prefect_server.sh
    x_monitor_run_prefect_worker.sh

src/
  services/
    x_monitor/
      __init__.py
      x_monitor_bootstrap.py
      x_monitor_cli.py
      x_monitor_config_loader.py
      x_monitor_database.py
      x_monitor_digest.py
      x_monitor_gmail_api.py
      x_monitor_gmail_smtp.py
      x_monitor_matching.py
      x_monitor_models.py
      x_monitor_notifications.py
      x_monitor_polling.py
      x_monitor_tables.py
      x_monitor_targets_sync.py
      x_monitor_text_normalizer.py
      x_monitor_twscrape_client.py
      templates/
        digest.html.j2
        digest.txt.j2
        immediate_alert.html.j2
        immediate_alert.txt.j2
        operator_alert.txt.j2

tests/
  unit/
    x_monitor/
      __init__.py
      conftest.py
      test_x_monitor_cli.py
      test_x_monitor_config_loader.py
      test_x_monitor_deployment_docs.py
      test_x_monitor_digest.py
      test_x_monitor_gmail_api.py
      test_x_monitor_gmail_smtp.py
      test_x_monitor_matching.py
      test_x_monitor_notebook_contract.py
      test_x_monitor_notebook_flow.py
      test_x_monitor_notifications.py
      test_x_monitor_polling.py
      test_x_monitor_settings.py
      test_x_monitor_tables.py
      test_x_monitor_targets_sync.py
      test_x_monitor_text_normalizer.py
      test_x_monitor_twscrape_client.py
```

---

## Task 1: Add dependency and settings scaffolding

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`
- Modify: `src/shared_utils/config.py`
- Create: `tests/unit/x_monitor/__init__.py`
- Create: `tests/unit/x_monitor/test_x_monitor_settings.py`
- Test: `tests/unit/test_config.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from src.shared_utils.config import get_settings


def test_x_monitor_settings_defaults():
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.x_monitor_database_url == "postgresql://localhost:5432/x_monitor"
    assert settings.x_monitor_config_path == Path("./config/x_monitor/x_monitor_targets.yaml")
    assert settings.x_monitor_workspace_dir == Path("./data/x_monitor")
    assert settings.x_monitor_twscrape_accounts_db == Path("./data/x_monitor/twscrape/accounts.db")
    assert settings.x_monitor_gmail_provider == "gmail_smtp"
    assert settings.x_monitor_gmail_api_use_adc is False
    assert settings.x_monitor_poll_cron == "*/5 * * * *"
    assert settings.x_monitor_digest_cron == "0 8 * * *"
    assert settings.x_monitor_health_cron == "*/30 * * * *"
    assert settings.x_monitor_timezone == "Asia/Singapore"
    assert settings.x_monitor_poll_batch_limit == 25
    assert settings.x_monitor_immediate_alerts_enabled is True
    assert settings.x_monitor_daily_digest_enabled is True
    assert settings.x_monitor_subject_prefix == "[X Monitor]"
    assert settings.x_monitor_operator_emails == ""
    assert settings.x_monitor_consecutive_failure_threshold == 3
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_settings.py tests/unit/test_config.py -v`
Expected: FAIL because the settings fields do not exist yet.

**Step 3: Write minimal implementation**

Add:
- X monitor dependencies to `pyproject.toml`: `alembic`, `jinja2`, `twscrape`, `tenacity`, `google-api-python-client`, `google-auth`, `google-auth-oauthlib`
- feature-specific env vars to `.env.example`
- new settings in `src/shared_utils/config.py`, including:

```python
# X Monitor
x_monitor_database_url: str = Field(default="postgresql://localhost:5432/x_monitor")
x_monitor_config_path: Path = Field(default=Path("./config/x_monitor/x_monitor_targets.yaml"))
x_monitor_workspace_dir: Path = Field(default=Path("./data/x_monitor"))
x_monitor_twscrape_accounts_db: Path = Field(
    default=Path("./data/x_monitor/twscrape/accounts.db")
)
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

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_settings.py tests/unit/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml .env.example src/shared_utils/config.py tests/unit/x_monitor/__init__.py tests/unit/x_monitor/test_x_monitor_settings.py
git commit -m "feat: add x monitor dependency and settings scaffolding"
```

---

## Task 2: Add config models and YAML loader

**Files:**
- Create: `src/services/x_monitor/__init__.py`
- Create: `src/services/x_monitor/x_monitor_models.py`
- Create: `src/services/x_monitor/x_monitor_config_loader.py`
- Create: `config/x_monitor/x_monitor_targets.example.yaml`
- Create: `tests/unit/x_monitor/conftest.py`
- Create: `tests/unit/x_monitor/test_x_monitor_config_loader.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

import pytest

from src.services.x_monitor.x_monitor_config_loader import load_x_monitor_config


def test_load_x_monitor_config_applies_defaults(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        '''
runtime:
  timezone: Asia/Hong_Kong
  poll_batch_limit: 10
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
    keywords_any: ["launch"]
    alert_recipients: ["alerts@example.com"]
    digest_recipients: ["digest@example.com"]
''',
        encoding="utf-8",
    )

    config = load_x_monitor_config(config_path)

    assert config.runtime.timezone == "Asia/Hong_Kong"
    assert config.runtime.poll_batch_limit == 10
    assert config.runtime.immediate_alerts_enabled is True
    assert config.runtime.daily_digest_enabled is True
    assert config.runtime.subject_prefix == "[X Monitor]"
    assert config.targets[0].include_replies is False
    assert config.targets[0].include_retweets is False
    assert config.targets[0].media_only is False
    assert config.targets[0].active is True
    assert config.targets[0].keywords_any == ["launch"]


def test_load_x_monitor_config_rejects_duplicate_ids(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        '''
targets:
  - id: duplicate_target
    username: account_one
    alert_recipients: ["alerts@example.com"]
    digest_recipients: ["digest@example.com"]
  - id: duplicate_target
    username: account_two
    alert_recipients: ["alerts@example.com"]
    digest_recipients: ["digest@example.com"]
''',
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_x_monitor_config(config_path)


def test_load_x_monitor_config_no_rules_means_match_all(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        '''
targets:
  - id: catch_all
    username: some_account
    alert_recipients: ["alerts@example.com"]
    digest_recipients: ["digest@example.com"]
''',
        encoding="utf-8",
    )

    config = load_x_monitor_config(config_path)
    target = config.targets[0]

    assert target.keywords_any == []
    assert target.keywords_all == []
    assert target.regex_any == []
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_config_loader.py -v`
Expected: FAIL because the module and models do not exist yet.

**Step 3: Write minimal implementation**

Create config models following the ir_monitor pattern:

`x_monitor_models.py`:
- `XMonitorRuntime` — timezone, poll_batch_limit, poll_window_minutes, immediate_alerts_enabled, daily_digest_enabled, subject_prefix, workspace_dir, schedule_cron overrides
- `XMonitorDefaults` — include_replies, include_retweets, media_only
- `XMonitorTarget` — id, username, user_id, include_replies, include_retweets, media_only, keywords_any, keywords_all, regex_any, alert_recipients, digest_recipients, active
- `XMonitorConfig` — runtime, defaults, targets (with `validate_unique_target_ids` model_validator)
- `XMonitorMatchResult` — matched, matched_rules, match_reason
- `XMonitorNotificationPayload` — kind, provider, recipient, subject, text_body, html_body, idempotency_key, post_id, target_id
- `XMonitorNormalizedPost` — post_id, target_id, author_username, author_user_id, created_at, text_raw, text_normalized, url, is_reply, is_retweet, has_media, lang, raw_json

`x_monitor_config_loader.py`:
- `load_x_monitor_config(config_path: Path) -> XMonitorConfig`
- Merges defaults onto every target, just like ir_monitor_config_loader

Example YAML (`config/x_monitor/x_monitor_targets.example.yaml`):
```yaml
runtime:
  timezone: Asia/Singapore
  poll_batch_limit: 25
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
    keywords_any: ["launch", "GPT", "o1"]
    alert_recipients: ["alerts@example.com"]
    digest_recipients: ["digest@example.com"]
    active: true
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_config_loader.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/x_monitor/__init__.py src/services/x_monitor/x_monitor_models.py src/services/x_monitor/x_monitor_config_loader.py config/x_monitor/x_monitor_targets.example.yaml tests/unit/x_monitor/conftest.py tests/unit/x_monitor/test_x_monitor_config_loader.py
git commit -m "feat: add x monitor config models and loader"
```

---

## Task 3: Add SQLAlchemy table metadata and Alembic scaffolding

**Files:**
- Create: `alembic.ini` (with `x_monitor/` script_location)
- Create: `migrations/x_monitor/env.py`
- Create: `migrations/x_monitor/script.py.mako`
- Create: `migrations/x_monitor/versions/<timestamp>_create_x_monitor_schema.py`
- Create: `src/services/x_monitor/x_monitor_tables.py`
- Create: `src/services/x_monitor/x_monitor_database.py`
- Create: `tests/unit/x_monitor/test_x_monitor_tables.py`

**Step 1: Write the failing test**

```python
from src.services.x_monitor.x_monitor_tables import X_MONITOR_METADATA


def test_x_monitor_table_names_follow_repo_conventions():
    table_names = set(X_MONITOR_METADATA.tables)

    assert "tblXMonitorTargets" in table_names
    assert "tblXMonitorTargetWatermarks" in table_names
    assert "tblXMonitorPosts" in table_names
    assert "tblXMonitorPostMatches" in table_names
    assert "tblXMonitorNotificationEvents" in table_names
    assert "tblXMonitorFlowRuns" in table_names
    assert "tblXMonitorDigestBookmarks" in table_names
    assert "tblXMonitorOperatorEvents" in table_names


def test_x_monitor_indexes_follow_repo_conventions():
    targets = X_MONITOR_METADATA.tables["tblXMonitorTargets"]
    index_names = {index.name for index in targets.indexes}
    assert "idxTblXMonitorTargetsUsername" in index_names

    posts = X_MONITOR_METADATA.tables["tblXMonitorPosts"]
    post_index_names = {index.name for index in posts.indexes}
    assert "idxTblXMonitorPostsPostId" in post_index_names
    assert "idxTblXMonitorPostsTargetIdCreatedAt" in post_index_names

    notif = X_MONITOR_METADATA.tables["tblXMonitorNotificationEvents"]
    notif_index_names = {index.name for index in notif.indexes}
    assert "idxTblXMonitorNotificationEventsIdempotencyKey" in notif_index_names


def test_x_monitor_notification_events_has_idempotency_key_column():
    notif = X_MONITOR_METADATA.tables["tblXMonitorNotificationEvents"]
    column_names = {col.name for col in notif.columns}
    assert "idempotency_key" in column_names
    assert "kind" in column_names
    assert "provider" in column_names
    assert "status" in column_names
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_tables.py -v`
Expected: FAIL because the metadata module does not exist yet.

**Step 3: Write minimal implementation**

Define SQLAlchemy `MetaData` object with explicit tables using repo-native names:

Tables (all 8 from the spec):
- `tblXMonitorTargets` — id (UUID PK), username (text unique not null), user_id (text null), include_replies, include_retweets, media_only, keywords_any (JSON), keywords_all (JSON), regex_any (JSON), alert_recipients (JSON), digest_recipients (JSON), active, created_at, updated_at
- `tblXMonitorTargetWatermarks` — target_id (UUID PK/FK), last_seen_post_id, last_seen_post_time, last_successful_poll_at, last_attempted_poll_at, consecutive_failures, last_error
- `tblXMonitorPosts` — id (UUID PK), post_id (text unique), target_id (UUID FK), author_username, author_user_id, created_at, text_raw, text_normalized, url, is_reply, is_retweet, has_media, lang, raw_json (JSON), inserted_at
- `tblXMonitorPostMatches` — id (UUID PK), post_id (UUID FK), target_id (UUID FK), matched, matched_rules (JSON), match_reason, created_at
- `tblXMonitorNotificationEvents` — id (UUID PK), post_id (UUID FK null), target_id (UUID FK null), kind, provider, recipient, subject, status, attempt_count, last_attempt_at, sent_at, error_message, payload_json (JSON), idempotency_key (text unique), created_at
- `tblXMonitorFlowRuns` — id (UUID PK), flow_name, prefect_flow_run_id, started_at, finished_at, status, counts_json (JSON), error_message
- `tblXMonitorDigestBookmarks` — digest_key (text PK), window_start, window_end, sent_at, recipient
- `tblXMonitorOperatorEvents` — id (UUID PK), event_type, severity, message, details_json (JSON), created_at, dedupe_key (text null)

Indexes:
- `idxTblXMonitorTargetsUsername` — unique on username
- `idxTblXMonitorPostsPostId` — unique on post_id
- `idxTblXMonitorPostsTargetIdCreatedAt` — on (target_id, created_at desc)
- `idxTblXMonitorPostsCreatedAt` — on created_at desc
- `idxTblXMonitorPostMatchesTargetIdCreatedAt` — on (target_id, created_at desc)
- `idxTblXMonitorNotificationEventsIdempotencyKey` — unique on idempotency_key
- `idxTblXMonitorOperatorEventsDedupeKey` — on dedupe_key

`x_monitor_database.py`:
- `get_x_monitor_engine()` — create SQLAlchemy engine from `settings.x_monitor_database_url`
- `get_x_monitor_session()` — session factory

Alembic:
- `alembic.ini` with `script_location = migrations/x_monitor`
- `migrations/x_monitor/env.py` wired to `X_MONITOR_METADATA`
- Initial migration creating all tables

Note: Use JSON type (not JSONB) in table definitions so unit tests can run against in-memory SQLite. The Alembic migration should use `postgresql.JSONB` explicitly for the real PostgreSQL schema. This is the accepted tradeoff for testability.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_tables.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add alembic.ini migrations/x_monitor src/services/x_monitor/x_monitor_tables.py src/services/x_monitor/x_monitor_database.py tests/unit/x_monitor/test_x_monitor_tables.py
git commit -m "feat: add x monitor table metadata and alembic scaffolding"
```

---

## Task 4: Add text normalization and match evaluation

**Files:**
- Create: `src/services/x_monitor/x_monitor_text_normalizer.py`
- Create: `src/services/x_monitor/x_monitor_matching.py`
- Create: `tests/unit/x_monitor/test_x_monitor_text_normalizer.py`
- Create: `tests/unit/x_monitor/test_x_monitor_matching.py`

**Step 1: Write the failing test**

```python
# test_x_monitor_text_normalizer.py
from src.services.x_monitor.x_monitor_text_normalizer import normalize_post_text


def test_normalize_removes_zero_width_and_collapses_whitespace():
    assert normalize_post_text("Earn\u200bings   launch") == "earnings launch"


def test_normalize_applies_nfkc():
    assert normalize_post_text("ﬁnance") == "finance"


def test_normalize_strips_control_chars():
    assert normalize_post_text("hello\x00world") == "hello world"
```

```python
# test_x_monitor_matching.py
from src.services.x_monitor.x_monitor_matching import evaluate_target_match


def test_match_keywords_any():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": False,
            "keywords_any": ["earnings", "guidance"],
            "keywords_all": [],
            "regex_any": [],
        },
        post={
            "is_reply": False,
            "is_retweet": False,
            "has_media": False,
            "text_raw": "Quarterly earnings are out",
        },
    )
    assert result.matched is True
    assert "keywords_any" in result.matched_rules


def test_reject_reply_when_disabled():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": False,
            "keywords_any": [],
            "keywords_all": [],
            "regex_any": [],
        },
        post={
            "is_reply": True,
            "is_retweet": False,
            "has_media": False,
            "text_raw": "Some reply text",
        },
    )
    assert result.matched is False


def test_reject_retweet_when_disabled():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": False,
            "keywords_any": [],
            "keywords_all": [],
            "regex_any": [],
        },
        post={
            "is_reply": False,
            "is_retweet": True,
            "has_media": False,
            "text_raw": "RT: something",
        },
    )
    assert result.matched is False


def test_reject_no_media_when_media_only():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": True,
            "keywords_any": [],
            "keywords_all": [],
            "regex_any": [],
        },
        post={
            "is_reply": False,
            "is_retweet": False,
            "has_media": False,
            "text_raw": "No media here",
        },
    )
    assert result.matched is False


def test_match_with_media_when_media_only():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": True,
            "keywords_any": ["earnings"],
            "keywords_all": [],
            "regex_any": [],
        },
        post={
            "is_reply": False,
            "is_retweet": False,
            "has_media": True,
            "text_raw": "Quarterly earnings are out",
        },
    )
    assert result.matched is True


def test_match_keywords_all_requires_every_keyword():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": False,
            "keywords_any": [],
            "keywords_all": ["earnings", "guidance"],
            "regex_any": [],
        },
        post={
            "is_reply": False,
            "is_retweet": False,
            "has_media": False,
            "text_raw": "Quarterly earnings are out",
        },
    )
    assert result.matched is False


def test_match_regex_any():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": False,
            "keywords_any": [],
            "keywords_all": [],
            "regex_any": [r"\bSEC\b", r"\bpartnership\b"],
        },
        post={
            "is_reply": False,
            "is_retweet": False,
            "has_media": False,
            "text_raw": "Filed with the SEC today",
        },
    )
    assert result.matched is True
    assert "regex_any" in result.matched_rules


def test_no_rules_means_match_all():
    result = evaluate_target_match(
        target={
            "include_replies": False,
            "include_retweets": False,
            "media_only": False,
            "keywords_any": [],
            "keywords_all": [],
            "regex_any": [],
        },
        post={
            "is_reply": False,
            "is_retweet": False,
            "has_media": False,
            "text_raw": "Any post at all",
        },
    )
    assert result.matched is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_text_normalizer.py tests/unit/x_monitor/test_x_monitor_matching.py -v`
Expected: FAIL because the modules do not exist yet.

**Step 3: Write minimal implementation**

`x_monitor_text_normalizer.py`:
- `normalize_post_text(text: str) -> str`
- lowercase + NFKC normalization
- collapse whitespace
- strip zero-width and control characters
- Do NOT mutate original rendered text used in email body

`x_monitor_matching.py`:
- `evaluate_target_match(target: dict, post: dict) -> XMonitorMatchResult`
- Rule evaluation order (from spec section 9.1):
  1. reject if retweet and `include_retweets=false`
  2. reject if reply and `include_replies=false`
  3. reject if `media_only=true` and no media
  4. normalize text
  5. if `keywords_any` non-empty, require at least one hit
  6. if `keywords_all` non-empty, require all hits
  7. if `regex_any` non-empty, require at least one hit
  8. if no rule lists defined, treat as match

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_text_normalizer.py tests/unit/x_monitor/test_x_monitor_matching.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/x_monitor/x_monitor_text_normalizer.py src/services/x_monitor/x_monitor_matching.py tests/unit/x_monitor/test_x_monitor_text_normalizer.py tests/unit/x_monitor/test_x_monitor_matching.py
git commit -m "feat: add x monitor normalization and matching logic"
```

---

## Task 5: Add repository helpers, targets sync, and idempotent persistence

**Files:**
- Create: `src/services/x_monitor/x_monitor_targets_sync.py`
- Create: `src/services/x_monitor/x_monitor_notifications.py`
- Create: `tests/unit/x_monitor/test_x_monitor_targets_sync.py`
- Create: `tests/unit/x_monitor/test_x_monitor_notifications.py`

**Step 1: Write the failing test**

```python
# test_x_monitor_targets_sync.py
def test_sync_targets_upserts_by_target_id(in_memory_x_monitor_engine):
    from src.services.x_monitor.x_monitor_targets_sync import sync_targets

    targets = [
        {
            "id": "openai_posts",
            "username": "openai",
            "alert_recipients": ["alerts@example.com"],
            "digest_recipients": ["digest@example.com"],
        }
    ]
    sync_targets(in_memory_x_monitor_engine, targets)

    # Upsert with changed recipients
    targets[0]["alert_recipients"] = ["ops@example.com"]
    sync_targets(in_memory_x_monitor_engine, targets)

    rows = list_targets(in_memory_x_monitor_engine)
    assert len(rows) == 1
    assert rows[0]["alert_recipients"] == ["ops@example.com"]


def test_sync_targets_deactivates_removed_targets(in_memory_x_monitor_engine):
    from src.services.x_monitor.x_monitor_targets_sync import sync_targets, list_targets

    sync_targets(in_memory_x_monitor_engine, [
        {"id": "old_target", "username": "old_account",
         "alert_recipients": ["a@b.com"], "digest_recipients": ["a@b.com"]}
    ])
    # Second sync with no targets — old one should be deactivated
    sync_targets(in_memory_x_monitor_engine, [])

    rows = list_targets(in_memory_x_monitor_engine, include_inactive=True)
    assert len(rows) == 1
    assert rows[0]["active"] is False
```

```python
# test_x_monitor_notifications.py
from src.services.x_monitor.x_monitor_notifications import generate_idempotency_key


def test_immediate_alert_idempotency_key():
    key = generate_idempotency_key(
        kind="immediate_alert",
        recipient="alerts@example.com",
        post_id="1234567890",
    )
    assert key == "immediate:alerts@example.com:1234567890"


def test_digest_idempotency_key():
    key = generate_idempotency_key(
        kind="digest",
        recipient="digest@example.com",
        window_start="2026-03-24T00:00:00",
        window_end="2026-03-24T23:59:59",
    )
    assert key == "digest:digest@example.com:2026-03-24T00:00:00:2026-03-24T23:59:59"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_targets_sync.py tests/unit/x_monitor/test_x_monitor_notifications.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

`x_monitor_targets_sync.py`:
- `sync_targets(engine, targets: list[dict])` — upsert into tblXMonitorTargets, deactivate targets not in the config
- `list_targets(engine, include_inactive=False) -> list[dict]`
- `ensure_watermark_row(engine, target_id: str)` — insert if not exists

`x_monitor_notifications.py`:
- `generate_idempotency_key(kind, recipient, post_id=None, window_start=None, window_end=None) -> str`
- `insert_notification_event(engine, event: dict) -> bool` — returns False if idempotency_key already exists with `sent` status
- `mark_notification_sent(engine, notification_id, sent_at)`
- `mark_notification_failed(engine, notification_id, error_message)`

Testing: Use `conftest.py` fixture `in_memory_x_monitor_engine` that creates all tables from `X_MONITOR_METADATA` in SQLite in-memory.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_targets_sync.py tests/unit/x_monitor/test_x_monitor_notifications.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/x_monitor/x_monitor_targets_sync.py src/services/x_monitor/x_monitor_notifications.py tests/unit/x_monitor/conftest.py tests/unit/x_monitor/test_x_monitor_targets_sync.py tests/unit/x_monitor/test_x_monitor_notifications.py
git commit -m "feat: add x monitor repository helpers and idempotency rules"
```

---

## Task 6: Add twscrape adapter and bootstrap behavior

**Files:**
- Create: `src/services/x_monitor/x_monitor_twscrape_client.py`
- Create: `src/services/x_monitor/x_monitor_bootstrap.py`
- Create: `tests/unit/x_monitor/test_x_monitor_twscrape_client.py`

**Step 1: Write the failing test**

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.x_monitor.x_monitor_twscrape_client import XMonitorTwscrapeClient


@pytest.fixture
def mock_twscrape_api():
    api = MagicMock()
    api.user_tweets = AsyncMock(return_value=[])
    api.user_tweets_and_replies = AsyncMock(return_value=[])
    api.user_by_login = AsyncMock(return_value=MagicMock(id=12345, username="openai"))
    return api


@pytest.mark.asyncio
async def test_client_uses_replies_endpoint_when_enabled(mock_twscrape_api):
    client = XMonitorTwscrapeClient(api=mock_twscrape_api)
    await client.fetch_recent_posts(user_id="123", include_replies=True, limit=25)
    mock_twscrape_api.user_tweets_and_replies.assert_called_once_with("123", limit=25)


@pytest.mark.asyncio
async def test_client_uses_posts_endpoint_when_replies_disabled(mock_twscrape_api):
    client = XMonitorTwscrapeClient(api=mock_twscrape_api)
    await client.fetch_recent_posts(user_id="123", include_replies=False, limit=25)
    mock_twscrape_api.user_tweets.assert_called_once_with("123", limit=25)


@pytest.mark.asyncio
async def test_client_resolves_user_id(mock_twscrape_api):
    client = XMonitorTwscrapeClient(api=mock_twscrape_api)
    user_id = await client.resolve_user_id("openai")
    assert user_id == "12345"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_twscrape_client.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

`x_monitor_twscrape_client.py`:
- `XMonitorTwscrapeClient` wrapping a twscrape API instance
- `resolve_user_id(username: str) -> str`
- `fetch_recent_posts(user_id: str, include_replies: bool, limit: int) -> list[dict]`
- Normalized post mapping: post_id, author_username, author_user_id, created_at, text_raw, url, is_reply, is_retweet, has_media, lang, raw_json

`x_monitor_bootstrap.py`:
- `bootstrap_target(engine, client, target) -> dict` — resolve user_id, fetch latest posts, set watermark to newest, do NOT alert on historical posts
- `backfill_target(engine, client, target, limit) -> dict` — explicit historical ingestion

Note: Add `pytest-asyncio` to dev dependencies in `pyproject.toml`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_twscrape_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/x_monitor/x_monitor_twscrape_client.py src/services/x_monitor/x_monitor_bootstrap.py tests/unit/x_monitor/test_x_monitor_twscrape_client.py pyproject.toml
git commit -m "feat: add x monitor twscrape adapter and bootstrap rules"
```

---

## Task 7: Add Gmail providers and template rendering

**Files:**
- Create: `src/services/x_monitor/x_monitor_gmail_smtp.py`
- Create: `src/services/x_monitor/x_monitor_gmail_api.py`
- Create: `src/services/x_monitor/templates/immediate_alert.txt.j2`
- Create: `src/services/x_monitor/templates/immediate_alert.html.j2`
- Create: `src/services/x_monitor/templates/digest.txt.j2`
- Create: `src/services/x_monitor/templates/digest.html.j2`
- Create: `src/services/x_monitor/templates/operator_alert.txt.j2`
- Create: `tests/unit/x_monitor/test_x_monitor_gmail_smtp.py`
- Create: `tests/unit/x_monitor/test_x_monitor_gmail_api.py`

**Step 1: Write the failing test**

```python
# test_x_monitor_gmail_smtp.py
from unittest.mock import patch, MagicMock

from src.services.x_monitor.x_monitor_gmail_smtp import GmailSmtpProvider


def test_gmail_smtp_provider_sends_email():
    provider = GmailSmtpProvider(
        host="smtp.gmail.com",
        port=587,
        username="test@gmail.com",
        password="app_password",
        from_addr="test@gmail.com",
        use_starttls=True,
    )

    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        result = provider.send_email(
            to=["alerts@example.com"],
            subject="[X Monitor] test",
            text_body="test body",
            html_body="<p>test body</p>",
        )

        assert result.sent is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@gmail.com", "app_password")
```

```python
# test_x_monitor_gmail_api.py
from unittest.mock import patch, MagicMock

from src.services.x_monitor.x_monitor_gmail_api import GmailApiProvider, build_gmail_api_credentials


def test_gmail_api_credentials_explicit_oauth(tmp_path):
    creds_file = tmp_path / "client.json"
    creds_file.write_text('{"installed": {}}', encoding="utf-8")
    token_file = tmp_path / "token.json"

    with patch("src.services.x_monitor.x_monitor_gmail_api.InstalledAppFlow") as mock_flow:
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_flow.from_client_secrets_file.return_value.run_local_server.return_value = mock_creds

        creds = build_gmail_api_credentials(
            credentials_file=str(creds_file),
            token_file=str(token_file),
            use_adc=False,
        )
        assert creds is not None


def test_gmail_api_credentials_adc_path():
    with patch("google.auth.default") as mock_default:
        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, "project-id")

        creds = build_gmail_api_credentials(
            credentials_file="",
            token_file="",
            use_adc=True,
        )
        assert creds is mock_creds
        mock_default.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_gmail_smtp.py tests/unit/x_monitor/test_x_monitor_gmail_api.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

`x_monitor_gmail_smtp.py`:
- `GmailSmtpProvider` class implementing the provider interface
- Uses `smtplib.SMTP` with STARTTLS on port 587
- Returns `SendResult(sent=True/False, error=None/str)`

`x_monitor_gmail_api.py`:
- `build_gmail_api_credentials(credentials_file, token_file, use_adc)` — returns google auth Credentials
  - If `use_adc=True`: calls `google.auth.default(scopes=[...])`
  - If `use_adc=False`: uses InstalledAppFlow with credentials_file
  - NEVER silently switch — raise clear error if chosen path is incomplete
- `GmailApiProvider` class using Gmail API `users.messages.send`
- Returns same `SendResult` type

Provider protocol (in `x_monitor_notifications.py` or models):
```python
class EmailProvider(Protocol):
    def send_email(
        self, *, to: list[str], subject: str, text_body: str,
        html_body: str | None, reply_to: str | None = None,
    ) -> SendResult: ...
```

Templates (Jinja2):
- `immediate_alert.txt.j2` / `.html.j2` — account handle, post timestamp, URL, full text, flags, matched rules
- `digest.txt.j2` / `.html.j2` — grouped by recipient then account, newest-first, time window, counts, links
- `operator_alert.txt.j2` — event type, severity, message, details

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_gmail_smtp.py tests/unit/x_monitor/test_x_monitor_gmail_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/x_monitor/x_monitor_gmail_smtp.py src/services/x_monitor/x_monitor_gmail_api.py src/services/x_monitor/x_monitor_notifications.py src/services/x_monitor/templates tests/unit/x_monitor/test_x_monitor_gmail_smtp.py tests/unit/x_monitor/test_x_monitor_gmail_api.py
git commit -m "feat: add x monitor gmail providers and templates"
```

---

## Task 8: Add polling and digest service orchestration

**Files:**
- Create: `src/services/x_monitor/x_monitor_polling.py`
- Create: `src/services/x_monitor/x_monitor_digest.py`
- Create: `tests/unit/x_monitor/test_x_monitor_polling.py`
- Create: `tests/unit/x_monitor/test_x_monitor_digest.py`

**Step 1: Write the failing test**

```python
# test_x_monitor_polling.py
from src.services.x_monitor.x_monitor_polling import (
    filter_unseen_posts,
    build_poll_run_summary,
)


def test_filter_unseen_posts_stops_at_watermark():
    posts = [
        {"post_id": "c", "created_at": "2026-03-24T03:00:00Z"},
        {"post_id": "b", "created_at": "2026-03-24T02:00:00Z"},
        {"post_id": "a", "created_at": "2026-03-24T01:00:00Z"},
    ]
    unseen = filter_unseen_posts(posts, last_seen_post_id="b")
    assert len(unseen) == 1
    assert unseen[0]["post_id"] == "c"


def test_filter_unseen_posts_returns_all_when_no_watermark():
    posts = [
        {"post_id": "c", "created_at": "2026-03-24T03:00:00Z"},
        {"post_id": "b", "created_at": "2026-03-24T02:00:00Z"},
    ]
    unseen = filter_unseen_posts(posts, last_seen_post_id=None)
    assert len(unseen) == 2
```

```python
# test_x_monitor_digest.py
from src.services.x_monitor.x_monitor_digest import group_digest_items


def test_group_digest_items_by_recipient_then_account():
    items = [
        {"recipient": "a@b.com", "username": "openai", "post_id": "1", "created_at": "2026-03-24T02:00:00Z"},
        {"recipient": "a@b.com", "username": "openai", "post_id": "2", "created_at": "2026-03-24T01:00:00Z"},
        {"recipient": "a@b.com", "username": "nvidia", "post_id": "3", "created_at": "2026-03-24T03:00:00Z"},
        {"recipient": "c@d.com", "username": "openai", "post_id": "4", "created_at": "2026-03-24T01:00:00Z"},
    ]
    grouped = group_digest_items(items)

    assert "a@b.com" in grouped
    assert "c@d.com" in grouped
    assert "openai" in grouped["a@b.com"]
    assert "nvidia" in grouped["a@b.com"]
    # newest-first within each account
    assert grouped["a@b.com"]["openai"][0]["post_id"] == "1"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_polling.py tests/unit/x_monitor/test_x_monitor_digest.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

`x_monitor_polling.py` — the core poll-run algorithm from spec section 13.1:
- `filter_unseen_posts(posts, last_seen_post_id) -> list[dict]`
- `build_poll_run_summary(results: list[dict]) -> dict` — counts for active targets, succeeded, failed, posts fetched, new inserts, matches, emails sent/failed, duration
- `poll_single_target(engine, client, email_provider, target, settings) -> dict` — orchestrates: load watermark → fetch → filter unseen → insert posts → evaluate matches → insert match records → create notification events → send immediate alerts → update watermark → return counts
- Transaction boundaries per spec:
  - TX A: insert posts + match records + pending notification rows
  - Outside TX: send email(s)
  - TX B: mark notification rows sent/failed + update watermark

`x_monitor_digest.py`:
- `group_digest_items(items: list[dict]) -> dict[str, dict[str, list[dict]]]` — grouped by recipient → account → newest-first
- `compute_digest_window(timezone: str) -> tuple[datetime, datetime]` — previous day's window
- `collect_digest_items(engine, window_start, window_end) -> list[dict]` — query matched posts not yet in a digest for each recipient
- `send_digest_for_recipient(engine, email_provider, recipient, items, window, settings) -> dict`

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_polling.py tests/unit/x_monitor/test_x_monitor_digest.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/x_monitor/x_monitor_polling.py src/services/x_monitor/x_monitor_digest.py tests/unit/x_monitor/test_x_monitor_polling.py tests/unit/x_monitor/test_x_monitor_digest.py
git commit -m "feat: add x monitor polling and digest service logic"
```

---

## Task 9: Add CLI utilities for local operator workflows

**Files:**
- Create: `src/services/x_monitor/x_monitor_cli.py`
- Create: `tests/unit/x_monitor/test_x_monitor_cli.py`

**Step 1: Write the failing test**

```python
from src.services.x_monitor.x_monitor_cli import build_parser


def test_cli_exposes_required_subcommands():
    parser = build_parser()
    subcommands = parser._subparsers._group_actions[0].choices

    assert "sync-targets" in subcommands
    assert "import-cookies" in subcommands
    assert "test-email" in subcommands
    assert "bootstrap-targets" in subcommands
    assert "backfill" in subcommands
    assert "health" in subcommands
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_cli.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Module-based CLI entrypoint (no console script needed):
```bash
uv run python -m services.x_monitor.x_monitor_cli <subcommand>
```

Subcommands:
- `sync-targets` — reconcile YAML targets into DB
- `import-cookies` — seed twscrape account store
- `test-email` — send one test email to configured operator recipient
- `bootstrap-targets` — resolve user IDs, fetch latest posts, set initial watermarks (no alerts on historical)
- `backfill --username <name> --limit N` — explicit historical ingestion
- `health` — connectivity and status report (DB, Prefect, twscrape)

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/x_monitor/x_monitor_cli.py tests/unit/x_monitor/test_x_monitor_cli.py
git commit -m "feat: add x monitor operator cli"
```

---

## Task 10: Add Prefect + Marimo notebook flows

**Files:**
- Create: `notebooks/x_monitor/x_monitor_poll_accounts.py`
- Create: `notebooks/x_monitor/x_monitor_send_digest.py`
- Create: `notebooks/x_monitor/x_monitor_healthcheck.py`
- Create: `tests/unit/x_monitor/test_x_monitor_notebook_contract.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_x_monitor_poll_notebook_contains_required_contract():
    notebook_text = Path("notebooks/x_monitor/x_monitor_poll_accounts.py").read_text(
        encoding="utf-8"
    )

    assert "@app.function" in notebook_text
    assert '@flow(name="x-monitor-poll-accounts"' in notebook_text
    assert "notify_on_failure" in notebook_text
    assert 'mo.app_meta().mode == "edit"' in notebook_text
    assert 'mo.app_meta().mode == "script"' in notebook_text
    assert "def load_config(" in notebook_text or "def load_x_monitor_config(" in notebook_text
    assert "poll_single_target" in notebook_text or "poll_targets" in notebook_text
    assert "update_watermark" in notebook_text or "watermark" in notebook_text


def test_x_monitor_digest_notebook_contains_required_contract():
    notebook_text = Path("notebooks/x_monitor/x_monitor_send_digest.py").read_text(
        encoding="utf-8"
    )

    assert "@app.function" in notebook_text
    assert '@flow(name="x-monitor-send-digest"' in notebook_text
    assert "group_digest_items" in notebook_text or "digest" in notebook_text
    assert 'mo.app_meta().mode == "edit"' in notebook_text
    assert 'mo.app_meta().mode == "script"' in notebook_text


def test_x_monitor_healthcheck_notebook_contains_required_contract():
    notebook_text = Path("notebooks/x_monitor/x_monitor_healthcheck.py").read_text(
        encoding="utf-8"
    )

    assert "@app.function" in notebook_text
    assert '@flow(name="x-monitor-healthcheck"' in notebook_text
    assert 'mo.app_meta().mode == "edit"' in notebook_text
    assert 'mo.app_meta().mode == "script"' in notebook_text
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_notebook_contract.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Create three notebooks following the repo's unified notebook pattern exactly (see `notebooks/ir/ir_webchanges_monitor.py` for reference).

Each notebook must have:
- PEP 723 dependency header
- `app = marimo.App(width="medium")`
- `with app.setup:` shared imports from `services.x_monitor.*` and `shared_utils.config`
- `@app.function` before every `@task` / `@flow`
- `edit` mode cells with interactive widgets
- `script` mode cell that runs the flow with dev defaults
- `if __name__ == "__main__": app.run()`

**`x_monitor_poll_accounts.py`** — tasks:
- `load_config(config_path)` — load and validate YAML config
- `sync_targets(config, engine)` — reconcile config targets into DB
- `resolve_user_ids(engine, client, targets)` — bootstrap missing user_ids
- `poll_targets(engine, client, email_provider, targets, settings)` — iterate active targets, call `poll_single_target` for each
- `record_run_summary(engine, summary)` — write to tblXMonitorFlowRuns

Flow: `run_x_monitor_poll_accounts(config_path, environment)` — orchestrates all tasks

**`x_monitor_send_digest.py`** — tasks:
- `load_config(config_path)` — load config
- `compute_window(timezone)` — determine digest time window
- `collect_items(engine, window)` — query undigested matched posts
- `send_digests(engine, email_provider, grouped_items, window, settings)` — send one per recipient
- `record_bookmarks(engine, bookmarks)` — write to tblXMonitorDigestBookmarks

Flow: `run_x_monitor_send_digest(config_path, environment)`

**`x_monitor_healthcheck.py`** — tasks:
- `check_database(engine)` — verify DB connectivity
- `check_prefect(api_url)` — verify Prefect API reachable
- `check_twscrape(accounts_db)` — verify accounts exist and are usable
- `check_gmail(email_provider)` — optional connectivity smoke test

Flow: `run_x_monitor_healthcheck(config_path, environment)` — emit operator alert on repeated failures

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_notebook_contract.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add notebooks/x_monitor/x_monitor_poll_accounts.py notebooks/x_monitor/x_monitor_send_digest.py notebooks/x_monitor/x_monitor_healthcheck.py tests/unit/x_monitor/test_x_monitor_notebook_contract.py
git commit -m "feat: add x monitor prefect marimo notebooks"
```

---

## Task 11: Add deployments, macOS scripts, launchd assets, and docs

**Files:**
- Modify: `prefect.yaml`
- Modify: `README.md`
- Modify: `docs/ADDING_FLOWS.md`
- Create: `docs/x_monitor/x_monitor_setup.md`
- Create: `launchd/x_monitor_prefect_server.plist`
- Create: `launchd/x_monitor_prefect_worker.plist`
- Create: `scripts/macos/x_monitor_run_prefect_server.sh`
- Create: `scripts/macos/x_monitor_run_prefect_worker.sh`
- Create: `tests/unit/x_monitor/test_x_monitor_deployment_docs.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_prefect_yaml_contains_x_monitor_deployments():
    prefect_yaml = Path("prefect.yaml").read_text(encoding="utf-8")

    assert "x-monitor-poll-accounts-prod" in prefect_yaml
    assert "x-monitor-send-digest-prod" in prefect_yaml
    assert "x-monitor-healthcheck-prod" in prefect_yaml
    assert "notebooks/x_monitor/x_monitor_poll_accounts.py:run_x_monitor_poll_accounts" in prefect_yaml


def test_docs_reference_x_monitor_workflow():
    readme_text = Path("README.md").read_text(encoding="utf-8")
    setup_doc = Path("docs/x_monitor/x_monitor_setup.md").read_text(encoding="utf-8")

    assert "X monitor" in readme_text or "x_monitor" in readme_text
    assert "local-process-pool" in setup_doc
    assert "gcloud auth application-default login" in setup_doc
    assert "Gmail SMTP" in setup_doc
    assert "Gmail API" in setup_doc
    assert "launchd" in setup_doc


def test_launchd_plists_exist():
    assert Path("launchd/x_monitor_prefect_server.plist").exists()
    assert Path("launchd/x_monitor_prefect_worker.plist").exists()


def test_macos_scripts_exist_and_are_executable():
    server_script = Path("scripts/macos/x_monitor_run_prefect_server.sh")
    worker_script = Path("scripts/macos/x_monitor_run_prefect_worker.sh")
    assert server_script.exists()
    assert worker_script.exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_deployment_docs.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Update `prefect.yaml` with three new deployments (add a macOS pool anchor):

```yaml
definitions:
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
    every_30_min: &every_30_min
      cron: "*/30 * * * *"
      timezone: "Asia/Singapore"
```

Deployments:
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
      - *every_30_min
```

Pull step: Add a macOS-specific pull step alongside the existing Windows one (or make it dynamic).

macOS scripts (`scripts/macos/`):
- `x_monitor_run_prefect_server.sh` — cd into repo, activate venv, export env vars, start `prefect server start`
- `x_monitor_run_prefect_worker.sh` — cd into repo, activate venv, export env vars, start `prefect worker start --pool local-process-pool --type process`

launchd plists (`launchd/`):
- `x_monitor_prefect_server.plist` — LaunchAgent for the Prefect server
- `x_monitor_prefect_worker.plist` — LaunchAgent for the Prefect worker

Setup doc (`docs/x_monitor/x_monitor_setup.md`):
- Local PostgreSQL setup (Postgres.app or Homebrew)
- Creating the work pool
- Deploying the notebooks
- Choosing SMTP vs Gmail API
- Optional ADC flow
- launchd loading commands
- Manual smoke test steps

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/x_monitor/test_x_monitor_deployment_docs.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add prefect.yaml README.md docs/ADDING_FLOWS.md docs/x_monitor/x_monitor_setup.md launchd/x_monitor_prefect_server.plist launchd/x_monitor_prefect_worker.plist scripts/macos/x_monitor_run_prefect_server.sh scripts/macos/x_monitor_run_prefect_worker.sh tests/unit/x_monitor/test_x_monitor_deployment_docs.py
git commit -m "feat: add x monitor deployments and macos operations docs"
```

---

## Task 12: Update __init__.py and wire public API

**Files:**
- Modify: `src/services/x_monitor/__init__.py`

**Step 1: Write the failing test (implicit)**

Ensure all public imports work:
```python
from services.x_monitor import (
    load_x_monitor_config,
    XMonitorConfig,
    XMonitorTarget,
    XMonitorMatchResult,
)
```

**Step 2: Write implementation**

Wire `__init__.py` to export all public models and key functions with `__all__`.

**Step 3: Run full test suite**

Run: `uv run pytest tests/unit/x_monitor -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add src/services/x_monitor/__init__.py
git commit -m "feat: wire x monitor public API exports"
```

---

## Final verification checklist

After all tasks are implemented, run this exact verification sequence:

```bash
uv run pytest tests/unit/x_monitor -v
uv run pytest tests/unit/test_config.py -v
uv run ruff check src/services/x_monitor src/shared_utils/config.py notebooks/x_monitor tests/unit/x_monitor
uv run marimo check notebooks/x_monitor/x_monitor_poll_accounts.py notebooks/x_monitor/x_monitor_send_digest.py notebooks/x_monitor/x_monitor_healthcheck.py
```

Then perform these manual smoke checks on macOS:

1. `prefect server start` launches and the UI opens.
2. `prefect work-pool create --type process local-process-pool` succeeds if the pool does not already exist.
3. `uv run python -m services.x_monitor.x_monitor_cli sync-targets --config config/x_monitor/x_monitor_targets.yaml` succeeds.
4. `uv run python -m services.x_monitor.x_monitor_cli health` reports healthy DB, Prefect, and twscrape prerequisites.
5. `uv run python -m services.x_monitor.x_monitor_cli test-email` succeeds with the selected Gmail provider.
6. `prefect deploy --all` registers the new notebook deployments.
7. A new post from a monitored account produces exactly one immediate alert per recipient.
8. A daily digest produces exactly one digest send record per recipient and window.

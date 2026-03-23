# Prefect PostgreSQL Backup Workflow — Repo-Aligned Implementation Spec

**Date**: 2026-03-23  
**Status**: Draft  

## 1. Goal

Add a Windows-friendly PostgreSQL backup workflow that fits this repository's existing architecture:

- The workflow lives in a **single Marimo notebook** under `notebooks/`
- The same notebook is used for **interactive development** and **Prefect production runs**
- Shared logic that benefits from unit testing lives in `src/shared_utils/`
- Deployment is registered through `prefect.yaml`, not `flow.serve()`

This replaces the earlier standalone `pg_backup/` package approach, which does not match the repo's unified Prefect + Marimo pattern.

## 2. Repo Constraints To Follow

The implementation must follow these repo rules:

1. Use `@app.function` first, then `@task` / `@flow`
2. Put the flow directly inside a notebook, not a wrapper module
3. Use `mo.app_meta().mode` to separate edit-mode UI from script execution
4. Include a PEP 723 dependency header at the top of the notebook
5. Reuse existing shared modules where possible, especially:
   - `src/shared_utils/config.py`
   - `src/shared_utils/prefect_notifications.py`
6. Keep testing **unit-test focused** with mocked subprocess / filesystem / secrets
7. Do not introduce a second parallel app layout like `pg_backup/flow.py`, `pg_backup/tasks.py`, `pg_backup/config.py`

## 3. Proposed File Layout

Add or change only the pieces that fit the current repo shape:

```text
notebooks/
└── maintenance/
    └── maintenance_pg_backup.py

src/
└── shared_utils/
    ├── config.py                       # extend existing Settings
    └── shared_utils_postgres_backup.py # new pure helper module for command / path / checksum logic

tests/
└── unit/
    ├── test_shared_utils_postgres_backup.py
    └── test_maintenance_pg_backup.py

prefect.yaml                            # add deployment entry
```

Notes:

- `notebooks/maintenance/maintenance_pg_backup.py` is the primary deliverable.
- `src/shared_utils/shared_utils_postgres_backup.py` should stay free of Prefect decorators and contain pure helpers that are easy to unit test.
- No new top-level package such as `pg_backup/` should be created.

## 4. Functional Requirements

The workflow should:

1. Run on Windows process workers and support manual local execution
2. Back up one PostgreSQL database using `pg_dump`
3. Write backups in PostgreSQL **custom format** (`.dump`)
4. Generate a `.sha256` sidecar file for each dump
5. Verify the dump with `pg_restore -l` before retention pruning
6. Prune old backup artifacts based on retention days
7. Return a structured run summary from the flow
8. Log enough detail for operators to diagnose failures
9. Optionally send flow notifications through the repo's shared Prefect notification hooks

Important clarification:

- Use `.dump`, not `.dump.gz`, for the primary artifact.
- `pg_dump -F c` already produces PostgreSQL custom format with built-in compression support via `-Z`.
- Do **not** add a redundant gzip step in v1.

## 5. Recommended Notebook Design

Create `notebooks/maintenance/maintenance_pg_backup.py` using the same overall structure as the other repo notebooks.

### 5.1 Header and setup

The notebook should include:

- PEP 723 script header
- `import marimo`
- `app = marimo.App(...)`
- `with app.setup:` imports shared by exported functions

Suggested dependencies in the notebook header:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "prefect>=3.0.0,<4.0.0",
#     "pydantic-settings>=2.0.0",
# ]
# ///
```

The repo already depends on `prefect`, `marimo`, `pydantic-settings`, and PostgreSQL drivers, so the notebook should stay lightweight and lean on the project environment.

### 5.2 Exported Prefect tasks

The notebook should expose task functions like:

- `resolve_backup_config`
- `check_backup_prerequisites`
- `check_pg_connection`
- `run_pg_dump`
- `verify_dump`
- `write_checksum`
- `prune_old_backups`
- `build_backup_summary`

Each exported task must follow the correct decorator order:

```python
@app.function
@task(...)
def run_pg_dump(...):
    ...
```

### 5.3 Exported flow

The main flow should be something like:

```python
@app.function
@flow(
    name="pg-backup",
    log_prints=True,
    on_failure=[notify_on_failure],
    on_completion=[notify_on_success],
)
def run_pg_backup(...):
    ...
```

Notes:

- Reuse `src/shared_utils/prefect_notifications.py` rather than inventing a separate `notify.py`
- If success notifications are too noisy, the existing settings flags should control behavior
- The flow should return a summary dict with fields such as database, dump path, size bytes, checksum path, pruned file count, and completed timestamp

### 5.4 Mode-conditional cells

Use `mo.app_meta().mode` explicitly:

- In `edit` mode:
  - provide widgets for database name, backup directory, retention days, compression level, and dry-run
  - allow an operator to manually trigger a backup from the notebook
  - display the last few backup files and a summary table
- In `script` mode:
  - call `run_pg_backup()` so `python notebooks/maintenance/maintenance_pg_backup.py` performs a backup

This repo treats notebooks as both dev surface and runtime surface, so the interactive cells are part of the design, not optional garnish.

## 6. Shared Helper Module Design

Add `src/shared_utils/shared_utils_postgres_backup.py` for logic that should be unit tested without Marimo or Prefect.

Recommended responsibilities:

- build timestamped backup filenames
- build `pg_isready`, `pg_dump`, and `pg_restore` commands
- resolve backup artifact paths
- compute SHA-256 checksums
- select retention candidates
- normalize Windows paths for subprocess usage

Recommended helper surface:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PgBackupArtifacts:
    dump_file: Path
    checksum_file: Path


def build_dump_file_path(backup_dir: Path, database: str, now: datetime) -> Path: ...
def build_pg_isready_command(...) -> list[str]: ...
def build_pg_dump_command(...) -> list[str]: ...
def build_pg_restore_list_command(dump_file: Path) -> list[str]: ...
def calculate_sha256(file_path: Path) -> str: ...
def find_backup_files_to_prune(backup_dir: Path, retention_days: int, now: datetime) -> list[Path]: ...
```

This split keeps the notebook focused on orchestration while preserving the repo's preference for unit-testable shared utilities.

## 7. Configuration Strategy

Do **not** create a new `config.py` module for this feature. Extend `src/shared_utils/config.py`.

Add fields such as:

```python
pg_backup_host: str = "localhost"
pg_backup_port: int = 5432
pg_backup_user: str = "backup_user"
pg_backup_password: str = ""
pg_backup_password_block_name: str | None = None
pg_backup_database: str = "postgres"
pg_backup_output_dir: Path = Path("./data/backups/postgres")
pg_backup_retention_days: int = 30
pg_backup_schedule_cron: str = "0 2 * * *"
pg_backup_timezone: str = "Asia/Hong_Kong"
pg_backup_compression_level: int = 6
pg_backup_connect_timeout_seconds: int = 15
pg_backup_timeout_seconds: int = 3600
pg_backup_min_free_space_gb: int = 5
```

Secret resolution order should be:

1. `Prefect Secret` block if `pg_backup_password_block_name` is configured
2. `PG_BACKUP_PASSWORD` from environment / `.env`
3. Fail fast with a clear error

This keeps local development easy while making production deployment safer.

## 8. Flow Parameters

The flow should accept parameters that override settings when needed:

```python
def run_pg_backup(
    database: str | None = None,
    backup_dir: str | None = None,
    retention_days: int | None = None,
    compression_level: int | None = None,
    verify_restore: bool = True,
    dry_run: bool = False,
) -> dict:
    ...
```

Guidance:

- Parameter defaults should come from `get_settings()`
- Deployment configuration in `prefect.yaml` should override only what needs to differ by environment
- Keep host, port, user, password, and timeout values primarily in settings rather than hard-coded deployment parameters

## 9. Pre-flight Checks

Before `pg_dump`, the flow should validate:

1. `pg_isready` is available
2. `pg_dump` is available
3. `pg_restore` is available
4. target backup directory exists or can be created
5. PostgreSQL is reachable
6. free disk space is above a minimum threshold

Recommended minimum disk-space rule for v1:

- require at least `pg_backup_min_free_space_gb`
- if a previous dump exists, require free space >= max(min threshold, 2 x newest dump size)

Fail before starting the dump if these checks do not pass.

## 10. Backup Execution Rules

Use `subprocess.run(...)` with explicit argument lists, not shell strings.

Recommended `pg_dump` settings:

- `-F c` custom format
- `-Z <compression level>`
- `-v`
- `-f <dump path>`

Set `PGPASSWORD` only in the subprocess environment for the command execution path. Do not log it.

Example command shape:

```text
pg_dump -h localhost -p 5432 -U backup_user -F c -Z 6 -v -f D:\Backups\pg\mydb_20260323_020000.dump mydb
```

After dump creation:

1. verify with `pg_restore -l`
2. calculate SHA-256
3. prune expired backup artifacts
4. return a structured summary

## 11. Deployment Through `prefect.yaml`

Do not use `flow.serve()` in this repo for this workflow. Add a deployment entry to `prefect.yaml`.

Suggested deployment snippet:

```yaml
  - name: pg-backup-daily
    entrypoint: notebooks/maintenance/maintenance_pg_backup.py:run_pg_backup
    description: "Daily PostgreSQL logical backup"
    tags: [prod, maintenance, postgres, backup]
    parameters:
      database: "workflow_app"
      backup_dir: "D:/Backups/postgres"
      retention_days: 30
      compression_level: 6
      verify_restore: true
      dry_run: false
    work_pool: *windows_pool
    schedules:
      - cron: "0 2 * * *"
        timezone: "Asia/Hong_Kong"
```

This matches the existing repo deployment style:

- direct notebook entrypoint
- `windows-process-pool`
- explicit tags
- cron schedule in `prefect.yaml`

## 12. Notifications

For v1, integrate with the existing shared notification hooks rather than designing a new notification subsystem here.

Required behavior:

- attach `notify_on_failure`
- optionally attach `notify_on_success`
- keep notification behavior controlled by existing shared settings

Do not add Slack-specific or SMTP-specific code in this feature unless the shared notification layer is also being extended as part of separate work.

## 13. Recovery Procedure

Document and validate recovery using PostgreSQL tooling.

### 13.1 Full restore

```powershell
pg_restore -h localhost -p 5432 -U postgres -d mydb_restored ^
    --create --clean --verbose ^
    D:\Backups\postgres\mydb_20260323_020000.dump
```

### 13.2 Selective restore

```powershell
pg_restore -l D:\Backups\postgres\mydb_20260323_020000.dump > toc.txt
pg_restore -h localhost -p 5432 -U postgres -d mydb ^
    -L toc.txt D:\Backups\postgres\mydb_20260323_020000.dump
```

### 13.3 Checksum validation

```powershell
$hash = (Get-FileHash -Algorithm SHA256 .\mydb_20260323_020000.dump).Hash.ToLower()
$expected = (Get-Content .\mydb_20260323_020000.dump.sha256).Split(" ")[0]
if ($hash -eq $expected) { "Checksum OK" } else { "CHECKSUM MISMATCH" }
```

## 14. Testing Strategy

Stay aligned with the repo's testing philosophy.

### 14.1 Required unit tests

Add unit tests for:

- dump filename generation
- command construction
- checksum generation
- retention pruning selection
- password resolution precedence
- subprocess failure handling
- flow summary shape

### 14.2 Mocking requirements

Mock:

- `subprocess.run`
- `shutil.which`
- `shutil.disk_usage`
- `Path.mkdir`, `Path.iterdir`, `Path.stat`, `Path.unlink`
- `prefect.blocks.system.Secret.load`
- notification hooks where needed

### 14.3 Manual verification

Manual notebook verification is still expected:

```bash
marimo edit notebooks/maintenance/maintenance_pg_backup.py
python notebooks/maintenance/maintenance_pg_backup.py
```

Do not add notebook integration tests as part of this feature.

## 15. Acceptance Criteria

- [ ] `notebooks/maintenance/maintenance_pg_backup.py` exists and follows repo notebook structure
- [ ] All Prefect tasks and the flow use `@app.function` before `@task` / `@flow`
- [ ] The backup runs successfully in script mode
- [ ] The flow is deployable directly from `prefect.yaml`
- [ ] A `.dump` backup file is created with PostgreSQL custom format
- [ ] `pg_restore -l` verification runs before pruning
- [ ] A `.sha256` sidecar file is created
- [ ] Old artifacts are pruned according to retention settings
- [ ] The flow returns a structured summary dict
- [ ] Unit tests pass with mocked external dependencies

## 16. Out Of Scope For V1

The following are useful but should not block the first implementation:

- offsite copy to S3 / NAS / Azure Blob
- GPG encryption of backup files
- weekly restore-to-scratch-db validation
- backup of multiple databases in one flow run
- physical backups (`pg_basebackup`)
- custom Slack / SMTP notifier modules

These can be added later once the single-database logical backup notebook is stable.

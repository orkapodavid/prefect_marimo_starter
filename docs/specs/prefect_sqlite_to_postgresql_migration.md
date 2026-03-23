# Prefect Server: SQLite → PostgreSQL Migration (Windows)

**Goal:** Migrate a Prefect project's database layer from the default SQLite to PostgreSQL. This covers both Prefect's internal server database and any application-level SQLAlchemy database.

## Phase 1 — Infrastructure (Manual / Terminal)

### 1.1 Install PostgreSQL

Download and install from https://www.postgresql.org/download/windows/ (use the EDB installer).

During installation:
- Note the port (default `5432`) and the superuser password you set
- Ensure "Command Line Tools" is checked

After install, add PostgreSQL's `bin` directory to your `PATH` if not already:
```powershell
# Typical path — adjust version number as needed
$env:PATH += ";C:\Program Files\PostgreSQL\17\bin"
```

### 1.2 Create Databases

Open a terminal (PowerShell or Command Prompt):
```powershell
# Create the Prefect server database
createdb -U postgres prefect_server
psql -U postgres prefect_server -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
# pg_trgm is REQUIRED by Prefect for text search — without it, schema creation fails

# If the app has its own SQLAlchemy database:
createdb -U postgres workflow_app
```

> You may be prompted for the `postgres` superuser password you set during installation.

### 1.3 Configure Prefect

```powershell
# Configure Prefect to use PostgreSQL
prefect config set PREFECT_API_DATABASE_CONNECTION_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/prefect_server"

# Initialize Prefect schema in PostgreSQL
prefect server database upgrade -y
```

## Phase 2 — Code Changes

Make these 3 changes in the codebase:

**1. Add PostgreSQL driver dependencies** (in `pyproject.toml`, `requirements.txt`, or equivalent):
```
psycopg2-binary>=2.9.0   # Sync SQLAlchemy driver (for app code)
asyncpg>=0.30.0           # Async driver (required by Prefect internally)
```

**2. Update the default database URL** in the app's settings/config module:
```diff
-database_url = "sqlite:///data/app.db"
+database_url = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/<app_db_name>"
```
This is typically in a Pydantic `Settings` class, Django `settings.py`, or a `config.py`. The env var `DATABASE_URL` should still override it.

**3. Update `.env.example`** (or equivalent env template):
```diff
-# DATABASE_URL=sqlite:///data/app.db
+DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/<app_db_name>
+# For SQLite (legacy): DATABASE_URL=sqlite:///data/app.db
+
+# Prefect server database (alternatively set via `prefect config set`)
+# PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/prefect_server
```

## Phase 3 — Data Migration (Optional)

Only if historical Prefect data (flow runs, task runs) must be preserved:

```powershell
# Back up first
copy %USERPROFILE%\.prefect\prefect.db %USERPROFILE%\.prefect\prefect.db.backup

# Option A: Use pgloader via WSL
wsl pgloader "sqlite:///mnt/c/Users/<username>/.prefect/prefect.db" ^
  "postgresql://postgres:YOUR_PASSWORD@localhost/prefect_server" ^
  --with "data only" --with "reset sequences"

# Option B: Use DBeaver or another GUI tool to export SQLite → import PostgreSQL
```

> **Note:** `pgloader` does not have a native Windows build. Use WSL (Windows Subsystem for Linux) or Docker to run it: `docker run --rm dimitri/pgloader pgloader ...`

## Phase 4 — Verify

```powershell
# Start Prefect server
prefect server start

# Check UI at http://localhost:4200

# Run existing tests (they should use sqlite:///:memory: and remain green)
pytest tests/ -v
```

## Key Rules

- **Do NOT change test fixtures** — tests should continue using `sqlite:///:memory:` for speed and CI portability
- Prefect uses `postgresql+asyncpg://` (async driver), your app's sync SQLAlchemy uses `postgresql://` (which resolves to `psycopg2`)
- The `pg_trgm` PostgreSQL extension is mandatory — Prefect's schema migration will fail without it
- `prefect server database upgrade -y` must run BEFORE starting the server with PostgreSQL
- On Windows, PostgreSQL runs as a Windows service by default (started automatically after installation)
- Replace `YOUR_PASSWORD` with the password set during PostgreSQL installation

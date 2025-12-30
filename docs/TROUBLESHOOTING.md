# Troubleshooting

## Common Issues

### 1. Notebook Execution Error
**Problem**: Prefect task fails with `NotebookExecutionError`.
**Solution**:
- Check the Prefect logs for the specific traceback.
- Ensure the notebook has a `@app.function` decorated entry point if being called with parameters.
- Verify all dependencies required by the notebook are installed in the environment.

### 2. Configuration Not Loading
**Problem**: Settings are using default values instead of `.env` values.
**Solution**:
- Ensure `.env` is in the root directory.
- Check `src/shared_utils/config.py` for any parsing errors.
- Verify environment variables are set correctly if not using `.env`.

### 3. Windows Service Won't Start
**Problem**: `PrefectWorker` service fails to start or crashes.
**Solution**:
- Check the logs in the configured logs directory (default: `logs/`).
- Ensure `nssm.exe` is configured correctly.
- Verify the service account has permission to read the project directory and execute Python.

### 4. Database Connection Failure
**Problem**: Cannot connect to SQLite, PostgreSQL, or MS SQL.
**Solution**:
- For SQLite, ensure the `data/` directory is writable.
- For PostgreSQL/MS SQL, verify the connection string variables in `.env`.

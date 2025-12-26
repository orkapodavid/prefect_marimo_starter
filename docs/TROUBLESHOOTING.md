# Troubleshooting

## Common Issues

### 1. Notebook Execution Error
**Problem**: Prefect task fails with `NotebookExecutionError`.
**Solution**:
- Check the Prefect logs for the specific traceback.
- Ensure the notebook has a `run(parameters)` function if being called with parameters.
- Verify all dependencies required by the notebook are installed in the environment.

### 2. Configuration Not Loading
**Problem**: Settings are using default values instead of YAML or `.env` values.
**Solution**:
- Ensure `config/settings.yaml` exists and is formatted correctly.
- Ensure `.env` is in the root directory.
- Check `src/workflow_utils/config.py` for any parsing errors.

### 3. Windows Service Won't Start
**Problem**: `PrefectWorker` service fails to start or crashes.
**Solution**:
- Check the logs in `logs/workers/`.
- Ensure `nssm.exe` is configured correctly.
- Verify the service account has permission to read the project directory and execute Python.

### 4. Database Connection Failure
**Problem**: Cannot connect to SQLite or PostgreSQL.
**Solution**:
- For SQLite, ensure the `data/` directory is writable.
- For PostgreSQL, verify the `DATABASE_URL` in `.env` or `settings.yaml`.

# Fix Local Setup and Tests

## Problem Statement

The current project has several issues preventing local development setup and test execution:

1. **Missing Package Installation**: The `src` directory is not installed as an editable package, causing import failures when running notebooks or tests
2. **Missing Data Directories**: Required directories referenced in notebooks and deployments do not exist
3. **Test Configuration Gap**: Unit tests assume certain environment variables that may not be set
4. **Missing Environment File**: No `.env` file exists for local development

## Objectives

Enable developers to successfully:
- Set up the local development environment following README instructions
- Run all notebooks in script mode without import errors
- Execute all unit tests with passing results
- Deploy flows to local Prefect server

## Root Causes Analysis

### Issue 1: Import Path Resolution

**Symptom**: Running `python notebooks/etl/daily_data_sync.py` or `pytest` results in `ModuleNotFoundError: No module named 'src'`

**Root Cause**: The project structure uses `src/` layout but the package is not installed in editable mode. Python cannot resolve imports like `from src.shared_utils.config import Settings` because `src` is not in the Python path.

**Current State**: 
- `pyproject.toml` defines the package structure with `where = ["src"]`
- README shows `uv sync` command
- No explicit editable install command documented

### Issue 2: Missing Runtime Directories

**Symptom**: Notebooks fail when attempting to write output files because parent directories don't exist

**Current References**:
- `notebooks/etl/daily_data_sync.py` uses paths like `data/input/daily.parquet` and `data/output/synced.parquet`
- `prefect.yaml` references `data/dev/input.parquet`, `data/dev/output.parquet`
- `src/shared_utils/config.py` defaults reference `./data`, `./logs`, `./reports`

**Existing Mitigation**: The `daily_data_sync.py` notebook creates parent directories using `Path(dest_path).parent.mkdir(parents=True, exist_ok=True)` but only for the output path, not input paths.

### Issue 3: Environment Configuration

**Symptom**: Tests and notebooks may behave inconsistently without environment configuration

**Current State**:
- `.env.example` exists with comprehensive variable definitions
- No `.env` file created during setup
- `src/shared_utils/config.py` uses pydantic-settings with defaults

### Issue 4: Test Isolation

**Symptom**: Unit tests modify global state that could affect subsequent test runs

**Current State**:
- `tests/unit/test_config.py` calls `get_settings.cache_clear()` manually
- `tests/conftest.py` sets environment variables via `autouse=True` fixture but doesn't ensure cleanup
- LRU cache on `get_settings()` persists across test functions

## Solution Design

### Solution 1: Package Installation Enhancement

**Approach**: Ensure the project is installed as an editable package during environment setup

**Implementation Strategy**:

Update the setup workflow to include explicit editable installation:

| Step | Action | Command | Purpose |
|------|--------|---------|---------|
| 1 | Install uv | Platform-specific install script | Package manager |
| 2 | Sync dependencies | `uv sync` | Install all dependencies from lock file |
| 3 | Install package | `uv pip install -e .` | Make `src` importable as installed package |
| 4 | Activate environment | `source .venv/bin/activate` (Mac/Linux) or `.venv\Scripts\activate` (Windows) | Use installed packages |

**Rationale**: The `uv sync` command installs dependencies but may not automatically install the current project in editable mode. Explicit editable installation ensures `src` modules are discoverable.

**Alternative Considered**: Adding `sys.path.append()` to notebooks - rejected because it violates AGENTS.md guidelines and doesn't work for tests.

### Solution 2: Directory Structure Initialization

**Approach**: Create required directory structure during initial setup

**Required Directories**:

```
data/
├── input/
├── output/
├── dev/
│   ├── input/
│   └── output/
├── sample/
logs/
reports/
sql/
```

**Implementation Strategy**:

Create a setup validation script that:
- Checks for existence of required directories
- Creates missing directories with appropriate `.gitkeep` files
- Validates that key paths referenced in configuration are accessible

**Location**: Add as `scripts/local/validate-setup.sh` (Mac/Linux) and `scripts/local/validate-setup.ps1` (Windows)

**Integration Point**: Execute this script as part of the documented setup process in README.md

### Solution 3: Environment Configuration

**Approach**: Provide clear guidance and automation for environment file creation

**Implementation Strategy**:

Add a step to the setup workflow:

| When | Action | Details |
|------|--------|---------|
| After `uv sync` | Copy environment template | `cp .env.example .env` (Mac/Linux) or `copy .env.example .env` (Windows) |
| Purpose | Ensure default configuration exists | Allows notebooks and tests to load settings consistently |

**Note**: The `.env` file should remain in `.gitignore` to prevent committing sensitive credentials.

### Solution 4: Test Fixture Improvements

**Approach**: Enhance test fixtures to ensure complete isolation between test functions

**Current Issues**:
- `get_settings()` uses `@lru_cache` which persists across tests
- Environment variable changes in one test can affect others
- No automatic cache clearing between tests

**Enhancement Strategy**:

Add test fixtures to `tests/conftest.py`:

| Fixture | Scope | Purpose | Behavior |
|---------|-------|---------|----------|
| `reset_settings_cache` | function | Clear LRU cache | Auto-use fixture that clears `get_settings.cache_clear()` before each test |
| `isolated_env` | function | Clean environment | Saves original env vars, yields, restores after test |
| `temp_data_dir` | function | Temporary directories | Creates temp dir structure, yields path, cleans up after |

**Cache Clearing Approach**: Make cache clearing automatic via autouse fixture rather than manual calls in individual tests.

### Solution 5: Documentation Updates

**Approach**: Update README.md to reflect complete and accurate setup process

**Required Changes**:

Update the "Environment Setup" section to include:

1. Complete setup command sequence with editable install
2. Directory structure initialization step
3. Environment file creation step
4. Setup validation step
5. Troubleshooting section for common import errors

**Updated Workflow**:

```
Step 1: Install uv
Step 2: Clone repository and navigate to project root
Step 3: Run uv sync
Step 4: Install project in editable mode
Step 5: Copy .env.example to .env
Step 6: Validate setup (run validation script)
Step 7: Start Prefect infrastructure
Step 8: Verify setup (run a sample notebook)
```

## Implementation Checklist

### Phase 1: Core Fixes (Critical)

- [ ] Add editable install command to README setup section
- [ ] Create directory structure initialization script
- [ ] Add environment file copy step to README
- [ ] Update setup section in README with complete workflow
- [ ] Add `.gitkeep` files to preserve empty directories in git

### Phase 2: Test Improvements (High Priority)

- [ ] Add `reset_settings_cache` autouse fixture to conftest.py
- [ ] Add `isolated_env` fixture for environment isolation
- [ ] Add `temp_data_dir` fixture for file system tests
- [ ] Update existing tests to use new fixtures where appropriate

### Phase 3: Validation & Documentation (Medium Priority)

- [ ] Create `scripts/local/validate-setup.sh` script
- [ ] Create `scripts/local/validate-setup.ps1` script
- [ ] Add "Verifying Setup" section to README
- [ ] Add "Troubleshooting Common Issues" section to README
- [ ] Document the setup validation script usage

### Phase 4: Quality Assurance (Final)

- [ ] Test complete setup process on clean macOS environment
- [ ] Test complete setup process on clean Windows environment
- [ ] Verify all unit tests pass after setup
- [ ] Verify all notebooks run successfully in script mode
- [ ] Verify Prefect deployments work correctly

## Expected Outcomes

### Success Criteria

1. **Setup Success**: A developer following README instructions can set up the environment without errors
2. **Import Resolution**: All notebooks run successfully with `python notebooks/<path>/<name>.py`
3. **Test Success**: Running `pytest` executes all tests with 100% pass rate
4. **Deployment Success**: Running `prefect deploy --all` succeeds without errors
5. **Interactive Mode**: Running `marimo edit notebooks/<path>/<name>.py` works without import errors

### Verification Commands

| Test | Command | Expected Result |
|------|---------|-----------------|
| Unit Tests | `pytest` | All tests pass |
| Notebook Script | `python notebooks/etl/daily_data_sync.py` | Executes without import errors, generates output |
| Notebook Interactive | `marimo edit notebooks/etl/daily_data_sync.py` | Opens without errors |
| Deployment | `prefect deploy --all` | All deployments created successfully |
| Config Loading | `python -c "from src.shared_utils.config import get_settings; print(get_settings())"` | Prints settings object |

## Risk Assessment

### Low Risk Items

- Adding `.gitkeep` files to directories
- Copying `.env.example` to `.env`
- Updating documentation
- Adding new test fixtures

**Rationale**: These changes are additive and don't modify existing functionality.

### Medium Risk Items

- Adding editable install step
- Creating directory initialization script
- Auto-clearing LRU cache in tests

**Rationale**: Changes the setup process but follows standard Python practices. Existing environments may need re-setup.

**Mitigation**: Provide clear migration guide for existing developers.

### Dependencies

- Requires `uv` package manager (already documented)
- Requires Python 3.12+ (already specified)
- No new external dependencies needed

## Notes

### Design Principles Applied

1. **Fail Fast**: Validation scripts detect issues early in setup process
2. **Convention Over Configuration**: Use standard Python packaging practices (editable install)
3. **Test Isolation**: Each test runs in clean state without side effects
4. **Documentation First**: Clear, step-by-step instructions prevent setup failures

### Alignment with Project Guidelines

- Follows AGENTS.md prohibition against `sys.path.append()`
- Maintains compatibility with Windows deployment target
- Preserves existing notebook architecture (unified Marimo + Prefect)
- Supports both interactive and script execution modes

### Future Enhancements

Items out of scope for this design but worth considering:

- Automated setup script that runs all initialization steps
- Pre-commit hook to validate environment setup
- GitHub Actions workflow to test setup process
- Docker-based development environment for consistency

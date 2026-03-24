# Master Program: LLM Agent Implementation Protocol

> This document is a self-contained program for an LLM agent to implement a feature
> from a specification and implementation plan using strict test-driven development.
> It is designed to be portable across repos with similar structures.

---

## 1. Inputs

Before starting, you need three things:

| Input | Description | Example path |
|-------|-------------|--------------|
| **Spec** | The design document — the source of truth for *what* to build | `docs/specs/prefect_webchanges.md` |
| **Plan** | The task-by-task implementation plan — the source of truth for *how* to build it | `plans/2026-03-24-prefect-webchanges-implementation-plan.md` |
| **Repo** | The working repository with existing code, tests, and conventions | `.` (current directory) |

---

## 2. Bootstrap Protocol

Run these steps exactly once at the start of a session. Do not skip any step.

### 2.1 Understand the repo

1. Read the project README, CLAUDE.md, and any `docs/ADDING_FLOWS.md` or contributor guide.
2. Read `pyproject.toml` for dependencies, Python version, test configuration, and package layout.
3. Read the primary config module (e.g., `src/shared_utils/config.py`) to understand the settings pattern.
4. Read one existing notebook that follows the same pattern as the one you will create — pay attention to:
   - PEP 723 dependency block
   - `@app.function` before `@task` / `@flow`
   - `mo.app_meta().mode` guards for edit vs. script mode
   - import paths (with or without `src.` prefix)
5. Read one existing service module and its `__init__.py` to understand the export pattern.
6. Read the root `conftest.py` and one subdirectory `conftest.py` to understand fixtures.
7. Read the deployment file (e.g., `prefect.yaml`) to understand YAML anchors and deployment shape.

### 2.2 Establish a baseline

```bash
# Install dependencies and verify the environment
uv sync --extra dev
uv pip install -e .

# Run existing tests to establish a green baseline
uv run pytest tests/ -v --tb=short

# Verify linting passes
uv run ruff check src/ tests/
```

**Gate:** Do not proceed if the baseline is red. Fix or document pre-existing failures first.

### 2.3 Read the spec and plan

1. Read the spec document end-to-end. Note every:
   - hard requirement
   - explicit constraint ("do not…")
   - schema definition
   - file path
2. Read the implementation plan end-to-end. Note:
   - total number of tasks
   - dependency ordering between tasks
   - which files each task creates or modifies
   - the exact test code provided for each task
3. Cross-check that the plan covers every spec requirement. If gaps exist, note them in the plan before implementing.

### 2.4 Create a feature branch

```bash
git checkout -b feat/ir-webchanges-monitor
```

---

## 3. Task Execution Loop

For each task in the plan, execute this exact cycle. Do not batch tasks. Do not skip steps.

```
┌─────────────────────────────────────────────────────┐
│  READ task from plan                                │
│  ↓                                                  │
│  CHECK preconditions (dependency tasks completed?)  │
│  ↓                                                  │
│  WRITE the failing test                             │
│  ↓                                                  │
│  RUN test → must FAIL for the expected reason       │
│  ↓                                                  │
│  WRITE minimal implementation                       │
│  ↓                                                  │
│  RUN test → must PASS                               │
│  ↓                                                  │
│  RUN regression tests                               │
│  ↓                                                  │
│  RUN linter                                         │
│  ↓                                                  │
│  COMMIT                                             │
│  ↓                                                  │
│  LOG outcome                                        │
└─────────────────────────────────────────────────────┘
```

### 3.1 Read the task

Read the full task section from the plan. Identify:
- **Files** to create or modify
- **Test code** to write (copy exactly from the plan)
- **Implementation guidance** (function signatures, requirements)
- **Expected test commands and outcomes**
- **Commit message**

### 3.2 Check preconditions

If the task declares a dependency (e.g., "> Depends on: Task 4"), verify:
- The dependency task's commit exists in `git log`
- The dependency task's test still passes: run its test command
- The files it created exist and are importable

### 3.3 Write the failing test

1. Create the test file at the exact path listed in the plan.
2. Copy the test code from the plan verbatim. Do not modify it yet.
3. If the test file's parent directory does not exist, create it with any required `__init__.py`.

### 3.4 Run the test — expect failure

```bash
uv run pytest <test_path> -v
```

**Expected:** The test MUST fail. Check the failure reason:

| Failure reason | Action |
|----------------|--------|
| `ModuleNotFoundError` — the module doesn't exist yet | Correct. Proceed to implementation. |
| `ImportError` — wrong import path | Fix the import in the test. This is a plan bug — note it. |
| `FileNotFoundError` — fixture file missing | Create the fixture file first, then re-run. |
| Test passes unexpectedly | The feature already exists or the test is wrong. Investigate before proceeding. |
| Syntax error in test | Fix the test syntax. Note the plan bug. |

### 3.5 Write minimal implementation

1. Create or modify the source files listed in the plan.
2. Follow the function signatures and requirements in the plan exactly.
3. When the plan says "implement like:", treat the code as a contract — the function name, parameters, and return type are fixed; the body is yours to write.
4. Write the minimum code needed to pass the test. Do not add features beyond what the test exercises.
5. If the plan references fixture files you need to create (HTML, JSON, etc.), create them with realistic content that matches the test assertions.

**Import path rules:**
- In production code under `src/`: use package imports without `src.` prefix (e.g., `from services.ir_monitor.ir_monitor_models import ...`)
- In test code under `tests/`: use absolute imports with `src.` prefix (e.g., `from src.services.ir_monitor.ir_monitor_models import ...`)
- In notebook code under `notebooks/`: use package imports without `src.` prefix (e.g., `from shared_utils.config import ...`)
- Verify these conventions against the actual repo — they may differ.

### 3.6 Run the test — expect pass

```bash
uv run pytest <test_path> -v
```

**Expected:** PASS.

If it fails:

| Failure type | Action |
|--------------|--------|
| `AssertionError` — logic bug | Fix the implementation, not the test. Re-run. |
| `TypeError` / `AttributeError` — wrong interface | Check the plan's function signature. Fix implementation to match. |
| `ImportError` — circular or missing dependency | Restructure imports. May require updating `__init__.py`. |
| Fixture data doesn't match assertions | Update fixture data to match the test's expectations, not the other way around. |

Iterate until the test passes. Do not modify the test to match broken implementation — the test is the contract.

### 3.7 Run regression tests

```bash
# Run the full feature test suite so far
uv run pytest tests/unit/ir_monitor/ -v

# Run related existing tests that might break
uv run pytest tests/unit/test_config.py -v
```

**Gate:** All tests must pass. If a regression appears:
1. Identify which change caused it
2. Fix the regression without breaking the new test
3. If the fix requires changing the plan, document the deviation

### 3.8 Run linter

```bash
uv run ruff check <new_and_modified_files>
```

Fix any issues. Do not disable linting rules — fix the code.

### 3.9 Commit

Use the exact commit message from the plan:

```bash
git add <files listed in plan>
git commit -m "<message from plan>"
```

Rules:
- Only commit files listed in the plan's commit command, plus any unlisted files you had to create (fixtures, `__init__.py`, etc.)
- Never commit `.env`, credentials, or unrelated changes
- One commit per task — do not squash or batch

### 3.10 Log outcome

After the commit, mentally (or in notes) record:
- Task number: done
- Tests: pass/fail count
- Deviations from plan: list any
- Decisions made: list any ambiguities you resolved

---

## 4. Error Recovery Protocol

### 4.1 Test fails after implementation and you cannot fix it within 3 attempts

1. Stop.
2. Re-read the spec section relevant to this task.
3. Re-read the plan's implementation guidance.
4. Check if a prior task's implementation is subtly wrong (bad model field name, wrong function signature).
5. If the issue is in a prior task, fix it there and re-run all tests.
6. If the spec and plan are contradictory, follow the spec — it is the source of truth.

### 4.2 Implementation requires something not in the plan

If you discover you need:
- A new dependency: add it to `pyproject.toml` and the PEP 723 block
- A new model field: add it to `ir_monitor_models.py` and update the existing tests if needed
- A new utility function: add it to the appropriate helper module
- A new fixture file: create it in the correct fixture directory

Document each deviation in the plan's Notes section at the bottom.

### 4.3 The plan contradicts the spec

The spec wins. Adjust the plan and proceed. Common cases:
- Plan says field is optional, spec says required → make it required
- Plan omits a spec requirement → add it to the current or next appropriate task
- Plan's test assertions don't match spec's schema → update the test to match the spec

### 4.4 A task's test code has a bug

Fix the test, note the fix, and continue. The plan's test code is a starting point — the spec's requirements are the real contract.

---

## 5. Verification Protocol

After completing all implementation tasks, run the final verification task from the plan. This is typically the last task, structured as:

### 5.1 Full unit suite

```bash
uv run pytest tests/unit/ir_monitor/ -v
```

All tests must pass.

### 5.2 Regression suite

```bash
uv run pytest tests/unit/test_config.py tests/unit/test_prefect_notifications.py -v
```

No regressions allowed.

### 5.3 Static analysis

```bash
uv run ruff check src/services/ir_monitor/ scripts/ir_monitor/ notebooks/ir/ tests/unit/ir_monitor/
```

Zero issues.

### 5.4 Notebook validation

```bash
uv run marimo check notebooks/ir/ir_webchanges_monitor.py
```

Must pass. If the repo doesn't use marimo, substitute the appropriate notebook linter.

### 5.5 Manual smoke test

```bash
# Open the notebook in edit mode and verify controls render
marimo edit notebooks/ir/ir_webchanges_monitor.py

# Run in script mode and verify it completes (may fail on network — that's expected)
uv run python notebooks/ir/ir_webchanges_monitor.py
```

### 5.6 Deployment validation

```bash
# Verify the deployment config parses
prefect deploy --dry-run --name ir-webchanges-monitor-prod 2>&1 || echo "dry-run not supported, verify manually"
```

### 5.7 Fix any issues

If verification reveals issues:
1. Fix the code
2. Re-run the relevant test
3. Commit the fix with message: `fix: <describe what was fixed>`
4. Do NOT amend previous commits

---

## 6. Plan Update Protocol

The plan is a living document. Update it as you implement.

### 6.1 When to update

- A task required a deviation from the plan
- You discovered a missing step
- A test needed to be modified
- An assumption in the plan was wrong
- You added files not listed in the plan

### 6.2 How to update

Add a `> **Actual:**` annotation below the relevant step:

```markdown
**Step 3: Write minimal implementation**

...existing plan text...

> **Actual:** Also added `ir_monitor_pdf_normalizer.py` which was not in the original
> plan but was needed to satisfy the spec's PDF monitoring requirement.
```

### 6.3 Final status block

After all tasks are complete, add a status block at the top of the plan:

```markdown
> **Status:** COMPLETE
> **Completed:** 2026-03-25
> **Total tasks:** 12
> **Deviations:** 2 (documented inline)
> **Test count:** 24 tests, all passing
> **Coverage:** config, dates, urls, normalizers, bridge script, jobs builder,
>   runner, report parser, artifacts, notifier, notebook contract, deployment
```

---

## 7. Adaptation Guide

To use this master program in a different repo:

### 7.1 Discover conventions before implementing

Every repo has its own patterns. Before starting, answer these questions:

| Question | Where to find the answer |
|----------|--------------------------|
| What package manager? (`uv`, `pip`, `poetry`) | README, pyproject.toml |
| How are imports resolved? (editable install, `sys.path`, `pythonpath` in pytest config) | pyproject.toml `[tool.pytest.ini_options]`, `setup.cfg` |
| What's the import prefix in tests? (`src.`, none, project name) | Existing test files |
| What's the import prefix in production code? | Existing source files, `__init__.py` |
| What linter? (`ruff`, `flake8`, `pylint`) | pyproject.toml `[tool.ruff]`, `.flake8`, CI config |
| What test runner and config? | pyproject.toml `[tool.pytest.ini_options]` |
| Where do fixtures live? | Existing test directories |
| What deployment system? | README, CI config, deployment files |
| What notebook system? (Marimo, Jupyter, none) | Existing notebooks, dependencies |

### 7.2 Adapt the plan

Replace repo-specific paths and patterns:
- Import prefixes
- Test fixture locations
- Configuration file format and location
- Deployment file and anchor names
- Notebook patterns (Marimo cells vs. Jupyter cells vs. plain scripts)
- Commit message conventions (check `git log --oneline -20`)

### 7.3 Adapt this master program

The TDD loop (section 3) is universal. Adapt only:
- Section 2 bootstrap commands (package manager, install commands)
- Section 5 verification commands (linter, notebook checker)
- Import path rules in section 3.5

---

## 8. Critical Rules

These rules override everything else. Never break them.

1. **The spec is the source of truth.** When the plan and spec disagree, follow the spec.
2. **Write the test first.** Never write implementation before the failing test exists.
3. **Do not modify a test to match broken implementation.** Fix the implementation.
4. **One task, one commit.** Do not batch or skip.
5. **Run regressions after every task.** A green task that breaks an earlier task is not done.
6. **Do not add features beyond the spec.** No extra configurability, no premature abstraction.
7. **Do not introduce `sys.path` hacks.** Use the repo's existing import resolution mechanism.
8. **Preserve existing code style.** Match indentation, naming, docstring conventions of the host repo.
9. **Never commit secrets.** No `.env` values, API keys, or credentials in committed files.
10. **Document deviations.** Every departure from the plan must be noted in the plan.

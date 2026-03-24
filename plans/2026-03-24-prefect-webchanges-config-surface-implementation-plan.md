# IR Monitor Config Surface Simplification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify the IR monitor configuration contract by separating runtime settings from per-target defaults and by narrowing target schema fields to the selector modes the current implementation actually supports.

**Architecture:** Introduce a dedicated top-level `runtime` config model for workspace and notification behavior, while keeping `defaults` limited to fields that are actually merged onto targets. Preserve backward compatibility by accepting legacy runtime-like keys under `defaults` during a transition period, but normalize them into `config.runtime` before validation. Keep the current jobs builder and notebook behavior intact other than reading from the normalized runtime model and relaxing unnecessary target config requirements.

**Tech Stack:** Python 3.12, Prefect 3, Marimo, pydantic, PyYAML, pytest, ruff

---

### Task 1: Split runtime settings from target defaults

**Files:**
- Modify: `src/services/ir_monitor/ir_monitor_models.py`
- Modify: `src/services/ir_monitor/ir_monitor_config_loader.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_config_loader.py`

**Step 1: Write the failing tests**

Add loader tests that define the intended config contract:

```python
def test_load_monitor_config_reads_runtime_section_without_merging_into_targets(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
runtime:
  notify_on_no_change: true
  workspace_dir: ./data/ir_monitor/staging
  schedule_cron: "0 * * * 1-5"
defaults:
  timezone: Asia/Tokyo
targets:
  - id: mitsubishi_corp_ir_ja
    company_id: mitsubishi_corp
    company_name: Mitsubishi Corporation
    page_label: Japanese IR page
    page_url: https://example.com/ir
    user_visible_url: https://example.com/ir
    target_kind: html_list
    normalizer: generic_jp_ir_news
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_monitor_config(config_path)

    assert config.runtime.notify_on_no_change is True
    assert str(config.runtime.workspace_dir).endswith("data/ir_monitor/staging")
    assert config.runtime.schedule_cron == "0 * * * 1-5"
    assert not hasattr(config.targets[0], "notify_on_no_change")
```

```python
def test_load_monitor_config_normalizes_legacy_runtime_keys_from_defaults(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
defaults:
  timezone: Asia/Tokyo
  notify_on_no_change: true
  workspace_dir: ./data/ir_monitor/legacy
targets:
  - id: legacy_target
    company_id: legacy_company
    company_name: Legacy Company
    page_label: Legacy page
    page_url: https://example.com/legacy
    user_visible_url: https://example.com/legacy
    target_kind: html_list
    normalizer: generic_en_ir_news
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_monitor_config(config_path)

    assert config.runtime.notify_on_no_change is True
    assert str(config.runtime.workspace_dir).endswith("data/ir_monitor/legacy")
    assert config.targets[0].timezone == "Asia/Tokyo"
```

**Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/ir_monitor/test_ir_monitor_config_loader.py -v
```

Expected: FAIL because `MonitorConfig` has no `runtime` section and the loader still merges runtime-looking keys into each target.

**Step 3: Write minimal implementation**

Implement a dedicated runtime model and normalize the loader:

- add `MonitorRuntime` to `src/services/ir_monitor/ir_monitor_models.py`
- add `runtime: MonitorRuntime = Field(default_factory=MonitorRuntime)` to `MonitorConfig`
- reduce `MonitorDefaults` to fields that actually belong on targets:
  - `timezone`
  - `report_timezone`
- in `src/services/ir_monitor/ir_monitor_config_loader.py`:
  - split `payload["runtime"]` from `payload["defaults"]`
  - continue accepting legacy `notify_on_no_change`, `workspace_dir`, and `schedule_cron` under `defaults`
  - move those legacy keys into `runtime`
  - only merge true target defaults onto `targets`
- precedence rule:
  - `runtime.<field>` wins over legacy `defaults.<field>`
  - explicit target field wins over `defaults`

**Step 4: Run tests to verify they pass**

Run:

```bash
uv run pytest tests/unit/ir_monitor/test_ir_monitor_config_loader.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/ir_monitor_models.py src/services/ir_monitor/ir_monitor_config_loader.py tests/unit/ir_monitor/test_ir_monitor_config_loader.py
git commit -m "refactor: separate ir monitor runtime config from target defaults"
```

### Task 2: Read normalized runtime settings from the notebook flow

**Files:**
- Modify: `notebooks/ir/ir_webchanges_monitor.py`
- Test: `tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py`

**Step 1: Write the failing tests**

Add notebook contract assertions for the normalized runtime fields:

```python
def test_ir_monitor_notebook_uses_config_runtime_fallbacks():
    notebook_text = Path("notebooks/ir/ir_webchanges_monitor.py").read_text(encoding="utf-8")

    assert "config.runtime.workspace_dir" in notebook_text
    assert "config.runtime.notify_on_no_change" in notebook_text
```

Also add a small unit test around a helper if the runtime-resolution logic is extracted from the flow body.

**Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py -v
```

Expected: FAIL because the notebook currently reads `SETTINGS.ir_monitor_workspace_dir` directly and does not reference `config.runtime`.

**Step 3: Write minimal implementation**

Update `run_ir_webchanges_monitor()` and helper tasks so the precedence is explicit:

- `workspace_dir`: flow parameter -> `config.runtime.workspace_dir` -> `SETTINGS.ir_monitor_workspace_dir / environment`
- `notify_on_no_change`: flow parameter override if not `None`, otherwise `config.runtime.notify_on_no_change`

To support that precedence cleanly:

- change flow/task signatures from `notify_on_no_change: bool = False` to `notify_on_no_change: bool | None = None`
- keep interactive edit-mode controls and Prefect parameters aligned with that new optional override behavior

Do not change the jobs builder or notification service behavior.

**Step 4: Run tests to verify they pass**

Run:

```bash
uv run pytest tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add notebooks/ir/ir_webchanges_monitor.py tests/unit/ir_monitor/test_ir_monitor_notebook_contract.py
git commit -m "refactor: use normalized ir monitor runtime settings in notebook flow"
```

### Task 3: Narrow the target selector surface to supported behavior

**Files:**
- Modify: `src/services/ir_monitor/ir_monitor_models.py`
- Modify: `config/ir_monitor/ir_monitor_targets.example.yaml`
- Test: `tests/unit/ir_monitor/test_ir_monitor_config_loader.py`

**Step 1: Write the failing tests**

Add tests that reflect the actual supported selector behavior:

```python
def test_load_monitor_config_defaults_selector_type_for_normalizer_targets(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
targets:
  - id: mitsubishi_corp_ir_ja
    company_id: mitsubishi_corp
    company_name: Mitsubishi Corporation
    page_label: Japanese IR page
    page_url: https://example.com/ir
    user_visible_url: https://example.com/ir
    target_kind: html_list
    normalizer: generic_jp_ir_news
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_monitor_config(config_path)

    assert config.targets[0].selector_type == "custom_script"
    assert config.targets[0].selector == ""
```

```python
def test_load_monitor_config_rejects_unsupported_selector_type(tmp_path: Path):
    config_path = tmp_path / "targets.yaml"
    config_path.write_text(
        """
targets:
  - id: invalid_selector
    company_id: invalid_company
    company_name: Invalid Company
    page_label: Invalid selector
    page_url: https://example.com/invalid
    user_visible_url: https://example.com/invalid
    target_kind: html_list
    selector_type: css
    normalizer: generic_en_ir_news
    enabled: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="selector_type"):
        load_monitor_config(config_path)
```

**Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/ir_monitor/test_ir_monitor_config_loader.py -v
```

Expected: FAIL because `selector_type` is currently required and accepts arbitrary strings.

**Step 3: Write minimal implementation**

Tighten `MonitorTarget`:

- change `selector_type: str` to `selector_type: Literal["custom_script"] = "custom_script"`
- keep `selector: str = ""` for backward compatibility
- remove `selector_type` and `selector` from the required example config unless they are needed to explain implementation details

This keeps the runtime behavior unchanged while making the config surface honest about what is currently supported.

**Step 4: Run tests to verify they pass**

Run:

```bash
uv run pytest tests/unit/ir_monitor/test_ir_monitor_config_loader.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/services/ir_monitor/ir_monitor_models.py config/ir_monitor/ir_monitor_targets.example.yaml tests/unit/ir_monitor/test_ir_monitor_config_loader.py
git commit -m "refactor: simplify ir monitor selector config surface"
```

### Task 4: Refresh docs and spec to match the simplified contract

**Files:**
- Modify: `docs/specs/prefect_webchanges.md`
- Modify: `docs/ir_monitor/IR_MONITOR_CONFIGURATION.md`
- Modify: `docs/ir_monitor/IR_MONITOR_OVERVIEW.md`
- Modify: `README.md`
- Test: `tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py`

**Step 1: Write the failing test**

Add or update a documentation contract test that checks for the new `runtime:` section and the simplified target examples:

```python
def test_ir_monitor_docs_reference_runtime_section_and_optional_selector_fields():
    config_doc = Path("docs/ir_monitor/IR_MONITOR_CONFIGURATION.md").read_text(encoding="utf-8")
    spec_doc = Path("docs/specs/prefect_webchanges.md").read_text(encoding="utf-8")

    assert "runtime:" in config_doc
    assert "workspace_dir" in config_doc
    assert "notify_on_no_change" in config_doc
    assert "selector_type" in config_doc
    assert "defaults are merged onto every target" not in config_doc
    assert "runtime:" in spec_doc
```

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py -v
```

Expected: FAIL because the docs currently describe runtime fields as `defaults`.

**Step 3: Write minimal implementation**

Update docs to match the normalized contract:

- move `workspace_dir`, `notify_on_no_change`, and `schedule_cron` examples under `runtime:`
- describe `defaults` as target-only defaults
- describe `selector_type` as optional and currently fixed to `custom_script`
- keep backward-compatibility notes for legacy configs that still place runtime keys under `defaults`

**Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add docs/specs/prefect_webchanges.md docs/ir_monitor/IR_MONITOR_CONFIGURATION.md docs/ir_monitor/IR_MONITOR_OVERVIEW.md README.md tests/unit/ir_monitor/test_ir_monitor_deployment_docs.py
git commit -m "docs: align ir monitor docs with simplified config contract"
```

### Task 5: Full verification and plan status update

**Files:**
- Modify: `plans/2026-03-24-prefect-webchanges-config-surface-implementation-plan.md`

**Step 1: Run full verification**

Run:

```bash
uv run pytest tests/unit/ir_monitor -v
uv run pytest tests/unit/test_config.py tests/unit/test_prefect_notifications.py -v
uv run ruff check src/services/ir_monitor scripts/ir_monitor notebooks/ir/ir_webchanges_monitor.py tests/unit/ir_monitor
uv run marimo check notebooks/ir/ir_webchanges_monitor.py
```

Expected: PASS

**Step 2: Update plan status**

Add a status block at the top when implementation is complete:

```markdown
> **Status:** COMPLETE | PARTIAL | BLOCKED
> **Completed:** YYYY-MM-DD
> **Total tasks:** 5
> **Tasks completed:** N
> **Deviations:** N (documented inline)
> **Test count:** N tests, all passing
> **Blocking issues:** None
```

Document any deviations inline with `> **Actual:**`.

**Step 3: Commit**

```bash
git add plans/2026-03-24-prefect-webchanges-config-surface-implementation-plan.md
git commit -m "docs: update ir monitor config surface plan with outcomes"
```


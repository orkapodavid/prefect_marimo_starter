# Implementation Prompt: Add stock ticker grouping to IR monitor config

> **Repo:** prefect-marimo-workflows
> **Branch:** `feat/ir-webchanges-monitor`
> **Base SHA:** `457b7b4` (current HEAD)
> **Date:** 2026-03-24

## Context

The IR monitor feature is complete and passing all tests (29 unit tests, lint clean, marimo check clean). It monitors configured IR/news web pages via webchanges, parses diffs, writes artifacts, and sends notifications.

Currently, company metadata (`company_name`, `company_id`) is repeated on every target in the YAML config and there is no stock ticker concept. Grouping in artifacts and notifications uses `company_name` as the display key.

This prompt adds a top-level `companies` section to the config so that company identity (name, ticker, exchange) is defined once and referenced by `company_id` across targets. All downstream grouping (artifacts, notifications, metadata enrichment) should use the ticker as part of the display label.

## Requirements

1. **Config schema**: Add an optional `companies` mapping to `ir_monitor_targets.yaml`. Each entry is keyed by `company_id` and contains `name`, `ticker`, and `exchange`.
2. **Backward compatibility**: If `companies` is absent, the existing behavior (company_name on each target) must still work. If `companies` is present and a target's `company_id` matches an entry, the company entry's `name` overrides `company_name` on the target.
3. **Model changes**: Add `ticker` and `exchange` fields to `MonitorTarget` (optional, defaulting to `""`). Add a pydantic model for the company entry. Propagate ticker/exchange from the `companies` section to each target during config loading.
4. **Artifact grouping**: `changes.md` headers should read `## Company Name (TICKER)` when a ticker is present, falling back to `## Company Name` when it is not.
5. **Notification grouping**: The notification message should include the ticker next to the company name.
6. **Metadata enrichment**: `_target_metadata_by_id` in the notebook should include `ticker` and `exchange` so the report parser can propagate them to change events.
7. **`MonitorChangeEvent`**: Add optional `ticker` and `exchange` fields. The report parser must populate them from metadata.
8. **Example config update**: Update `config/ir_monitor/ir_monitor_targets.example.yaml` to demonstrate the `companies` section with at least two companies and tickers.

## Target config shape

```yaml
companies:
  mitsubishi_corp:
    name: Mitsubishi Corporation
    ticker: 8058.T
    exchange: TSE
  stellapharm:
    name: Stella Pharma
    ticker: STLA.VN
    exchange: HOSE

defaults:
  timezone: Asia/Tokyo
  report_timezone: Asia/Tokyo

targets:
  - id: mitsubishi_corp_ir_ja
    company_id: mitsubishi_corp          # resolved from companies section
    page_label: Japanese IR page
    page_url: https://www.mitsubishicorp.com/jp/ja/ir/
    user_visible_url: https://www.mitsubishicorp.com/jp/ja/ir/
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_jp_ir_news
    enabled: true

  - id: stellapharm_news_en
    company_id: stellapharm
    page_label: All Stella News
    page_url: https://stellapharm.com/news/all-stella-news/
    user_visible_url: https://stellapharm.com/news/all-stella-news/
    target_kind: html_list
    selector_type: custom_script
    normalizer: generic_en_ir_news
    language: en
    enabled: true
```

When `companies` is present, targets no longer need `company_name` — it resolves from `companies[company_id].name`. If a target still has `company_name` and conflicts with the companies entry, the companies entry wins.

## Files to modify

| File | Change |
|------|--------|
| `src/services/ir_monitor/ir_monitor_models.py` | Add `CompanyEntry` model. Add `ticker`, `exchange` to `MonitorTarget` and `MonitorChangeEvent`. Add `companies` field to `MonitorConfig`. |
| `src/services/ir_monitor/ir_monitor_config_loader.py` | Resolve `company_name`, `ticker`, `exchange` from `companies` section onto each target during loading. |
| `src/services/ir_monitor/ir_monitor_artifacts.py` | Update `_build_markdown` to include ticker in company headers. |
| `src/services/ir_monitor/ir_monitor_notifier.py` | Update `_build_message` to include ticker next to company names. |
| `src/services/ir_monitor/ir_monitor_report_parser.py` | Propagate `ticker` and `exchange` in `_event_metadata` and enrichment loop. |
| `notebooks/ir/ir_webchanges_monitor.py` | Include `ticker` and `exchange` in `_target_metadata_by_id`. |
| `config/ir_monitor/ir_monitor_targets.example.yaml` | Demonstrate `companies` section. |

## Files to add/modify for tests

| File | Change |
|------|--------|
| `tests/unit/ir_monitor/test_ir_monitor_config_loader.py` | Add test: companies section resolves name/ticker/exchange onto targets. Add test: missing companies section still works (backward compat). Add test: company_name on target is overridden by companies entry. |
| `tests/unit/ir_monitor/test_ir_monitor_artifacts.py` | Assert ticker appears in markdown output when present. Assert no parenthetical when ticker is empty. |
| `tests/unit/ir_monitor/test_ir_monitor_notifier.py` | Assert ticker appears in notification message. |
| `tests/unit/ir_monitor/test_ir_monitor_report_parser.py` | Assert ticker/exchange propagate through metadata enrichment. |

## Implementation order

1. **Update the plan** — Append a new task to `plans/2026-03-24-prefect-webchanges-implementation-plan.md` documenting this work as Task 13 (or the next available number). Follow the existing task format with failing-test-first steps.
2. **Models** — Add `CompanyEntry`, `companies` field, and new optional fields.
3. **Config loader** — Resolve companies onto targets.
4. **Tests for loader** — Write and run tests.
5. **Artifacts + notifier** — Update display formatting.
6. **Tests for artifacts + notifier** — Write and run tests.
7. **Report parser + notebook metadata** — Propagate ticker/exchange.
8. **Tests for parser** — Write and run tests.
9. **Example config** — Update the example YAML.
10. **Full verification** — Run the four-command verification suite:
    ```bash
    uv run pytest tests/unit/ir_monitor -v
    uv run pytest tests/unit/test_config.py tests/unit/test_prefect_notifications.py -v
    uv run ruff check src/services/ir_monitor scripts/ir_monitor notebooks/ir/ir_webchanges_monitor.py tests/unit/ir_monitor
    uv run marimo check notebooks/ir/ir_webchanges_monitor.py
    ```
11. **Update documentation** — Update `docs/specs/prefect_webchanges.md` configuration schema section to document the `companies` section. Update `README.md` if the setup instructions reference the example config.

## Constraints

- Read `AGENTS.md` at the repo root before starting — it contains critical rules for decorator stacking, imports, file naming, and temp file paths.
- Use test-first development: write the failing test, then implement, then verify.
- Do not break existing tests. All 29 current tests plus the new ones must pass.
- Do not change the normalizer logic, webchanges runner, or jobs builder — this change is config/display only.
- Keep `company_name` on `MonitorTarget` as a regular field (not removed) for backward compatibility. It gets overwritten during loading when a companies entry matches.
- Commit each logical step separately with descriptive messages.
- Temporary/scratch files go in `tmp/` at the repo root (git-ignored), never `/tmp/`.

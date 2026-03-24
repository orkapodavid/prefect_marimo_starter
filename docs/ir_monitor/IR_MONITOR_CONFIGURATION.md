# IR Monitor Configuration

User-facing config lives in `config/ir_monitor/ir_monitor_targets.yaml`.

## Top-Level Structure

```yaml
companies:
  mitsubishi_corp:
    name: Mitsubishi Corporation
    ticker: 8058.T
    exchange: TSE

runtime:
  notify_on_no_change: false
  workspace_dir: ./data/ir_monitor/prod
  schedule_cron: "0 * * * 1-5"

defaults:
  timezone: Asia/Tokyo
  report_timezone: Asia/Tokyo

targets:
  - id: mitsubishi_corp_ir_ja
    company_id: mitsubishi_corp
    page_label: Japanese IR page
    page_url: https://www.mitsubishicorp.com/jp/ja/ir/
    user_visible_url: https://www.mitsubishicorp.com/jp/ja/ir/
    target_kind: html_list
    normalizer: generic_jp_ir_news
    enabled: true
```

## `companies`

`companies` is optional.

Each key is a `company_id`, and each value supports:

- `name`
- `ticker`
- `exchange`

When a target references a matching `company_id`, the loader resolves:

- `company_name <- companies[company_id].name`
- `ticker <- companies[company_id].ticker`
- `exchange <- companies[company_id].exchange`

If the target also supplies `company_name`, the registry value wins.

## `runtime`

`runtime` is optional.

It controls run-level behavior that does not belong on individual targets:

- `notify_on_no_change`
- `workspace_dir`
- `schedule_cron`

During the transition, legacy configs may still place these keys under `defaults`.
The loader normalizes them into `config.runtime`, but new configs should use a top-level
`runtime:` section.

## `defaults`

`defaults` are merged onto every target before validation.

Important fields:

- `timezone`
- `report_timezone`

## `targets`

Required target fields:

- `id`
- `company_id`
- `page_label`
- `page_url`
- `user_visible_url`
- `target_kind`
- `normalizer`

Target-level `company_name` is still supported for backward compatibility, but it is
only required when no matching `companies` entry exists.

Optional target metadata now includes:

- `ticker`
- `exchange`

These are normally resolved from `companies`, but can still exist on the target model
after loading and enrichment.

Selector fields:

- `selector_type` is optional and currently fixed to `custom_script`
- `selector` is optional and defaults to `""`

## Backward Compatibility

These configs still work:

```yaml
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
```

Legacy runtime keys under `defaults` still work during the transition:

```yaml
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
```

This config is invalid because the target resolves to no company name:

```yaml
targets:
  - id: invalid_target
    company_id: missing_company
    page_label: Missing company name
    page_url: https://example.com/invalid
    user_visible_url: https://example.com/invalid
    target_kind: html_list
    normalizer: generic_en_ir_news
    enabled: true
```

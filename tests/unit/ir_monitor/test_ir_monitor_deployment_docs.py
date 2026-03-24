from pathlib import Path


def test_prefect_yaml_contains_ir_monitor_deployment():
    prefect_yaml = Path("prefect.yaml").read_text(encoding="utf-8")
    assert "ir-webchanges-monitor-prod" in prefect_yaml
    assert "notebooks/ir/ir_webchanges_monitor.py:run_ir_webchanges_monitor" in prefect_yaml
    assert "hourly_weekday_tokyo" in prefect_yaml


def test_docs_reference_ir_monitor_workflow():
    readme_text = Path("README.md").read_text(encoding="utf-8")
    adding_flows_text = Path("docs/ADDING_FLOWS.md").read_text(encoding="utf-8")

    assert "IR monitor" in readme_text
    assert "notebooks/ir/ir_webchanges_monitor.py" in adding_flows_text


def test_ir_monitor_docs_reference_runtime_section_and_optional_selector_fields():
    config_doc = Path("docs/ir_monitor/IR_MONITOR_CONFIGURATION.md").read_text(
        encoding="utf-8"
    )
    spec_doc = Path("docs/specs/prefect_webchanges.md").read_text(encoding="utf-8")

    assert "runtime:" in config_doc
    assert "workspace_dir" in config_doc
    assert "notify_on_no_change" in config_doc
    assert "selector_type" in config_doc
    assert "defaults are merged onto every target" not in config_doc
    assert "runtime:" in spec_doc

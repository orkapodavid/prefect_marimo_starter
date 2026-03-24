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

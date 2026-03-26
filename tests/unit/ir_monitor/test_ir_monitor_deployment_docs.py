from pathlib import Path

import yaml


def test_prefect_yaml_contains_ir_monitor_deployment():
    prefect_yaml = Path("prefect.yaml").read_text(encoding="utf-8")
    prefect_config = yaml.safe_load(prefect_yaml)
    deployments = {deployment["name"]: deployment for deployment in prefect_config["deployments"]}
    deployment = deployments["ir-webchanges-monitor-prod"]

    assert "ir-webchanges-monitor-prod" in prefect_yaml
    assert "notebooks/ir/ir_webchanges_monitor.py:run_ir_webchanges_monitor" in prefect_yaml
    assert "hourly_weekday_tokyo" in prefect_yaml
    assert "config_path" not in deployment["parameters"]
    assert deployment["pull"] == [
        {
            "prefect.deployments.steps.set_working_directory": {
                "directory": "/opt/prefect/prefect_marimo_starter"
            }
        }
    ]


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


def test_ir_monitor_example_config_uses_runtime_section_for_runtime_keys():
    example_config = yaml.safe_load(
        Path("config/ir_monitor/ir_monitor_targets.example.yaml").read_text(encoding="utf-8")
    )

    assert example_config["runtime"]["notify_on_no_change"] is False
    assert example_config["runtime"]["workspace_dir"] == "./data/ir_monitor/prod"
    assert example_config["runtime"]["schedule_cron"] == "0 * * * 1-5"
    assert "notify_on_no_change" not in example_config["defaults"]
    assert "workspace_dir" not in example_config["defaults"]
    assert "schedule_cron" not in example_config["defaults"]

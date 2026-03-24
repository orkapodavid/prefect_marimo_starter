from pathlib import Path


def test_prefect_yaml_contains_x_monitor_deployments():
    prefect_yaml = Path("prefect.yaml").read_text(encoding="utf-8")

    assert "x-monitor-poll-accounts-prod" in prefect_yaml
    assert "x-monitor-send-digest-prod" in prefect_yaml
    assert "x-monitor-healthcheck-prod" in prefect_yaml
    assert "notebooks/x_monitor/x_monitor_poll_accounts.py:run_x_monitor_poll_accounts" in (
        prefect_yaml
    )


def test_docs_reference_x_monitor_workflow():
    readme_text = Path("README.md").read_text(encoding="utf-8")
    setup_doc = Path("docs/x_monitor/x_monitor_setup.md").read_text(encoding="utf-8")

    assert "X monitor" in readme_text or "x_monitor" in readme_text
    assert "local-process-pool" in setup_doc
    assert "gcloud auth application-default login" in setup_doc
    assert "Gmail SMTP" in setup_doc
    assert "Gmail API" in setup_doc
    assert "launchd" in setup_doc


def test_launchd_plists_exist():
    assert Path("launchd/x_monitor_prefect_server.plist").exists()
    assert Path("launchd/x_monitor_prefect_worker.plist").exists()


def test_macos_scripts_exist_and_are_executable():
    server_script = Path("scripts/macos/x_monitor_run_prefect_server.sh")
    worker_script = Path("scripts/macos/x_monitor_run_prefect_worker.sh")
    assert server_script.exists()
    assert worker_script.exists()

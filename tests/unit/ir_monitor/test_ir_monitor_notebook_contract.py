from pathlib import Path


def test_ir_monitor_notebook_contains_required_flow_contract():
    notebook_text = Path("notebooks/ir/ir_webchanges_monitor.py").read_text(encoding="utf-8")

    assert "@app.function" in notebook_text
    assert '@flow(name="ir-webchanges-monitor"' in notebook_text
    assert "notify_on_failure" in notebook_text
    assert "def load_monitor_config(" in notebook_text
    assert "def prepare_workspace(" in notebook_text
    assert "def run_webchanges(" in notebook_text
    assert "def parse_webchanges_output(" in notebook_text
    assert "def write_artifacts(" in notebook_text
    assert "def notify_if_needed(" in notebook_text
    assert 'mo.app_meta().mode == "edit"' in notebook_text
    assert 'mo.app_meta().mode == "script"' in notebook_text

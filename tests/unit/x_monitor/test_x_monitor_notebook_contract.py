from pathlib import Path


def test_x_monitor_poll_notebook_contains_required_contract():
    notebook_text = Path("notebooks/x_monitor/x_monitor_poll_accounts.py").read_text(
        encoding="utf-8"
    )

    assert "@app.function" in notebook_text
    assert '@flow(name="x-monitor-poll-accounts"' in notebook_text
    assert "notify_on_failure" in notebook_text
    assert 'mo.app_meta().mode == "edit"' in notebook_text
    assert 'mo.app_meta().mode == "script"' in notebook_text
    assert "def load_config(" in notebook_text or "def load_x_monitor_config(" in notebook_text
    assert "poll_single_target" in notebook_text or "poll_targets" in notebook_text
    assert "update_watermark" in notebook_text or "watermark" in notebook_text


def test_x_monitor_digest_notebook_contains_required_contract():
    notebook_text = Path("notebooks/x_monitor/x_monitor_send_digest.py").read_text(
        encoding="utf-8"
    )

    assert "@app.function" in notebook_text
    assert '@flow(name="x-monitor-send-digest"' in notebook_text
    assert "group_digest_items" in notebook_text or "digest" in notebook_text
    assert 'mo.app_meta().mode == "edit"' in notebook_text
    assert 'mo.app_meta().mode == "script"' in notebook_text


def test_x_monitor_healthcheck_notebook_contains_required_contract():
    notebook_text = Path("notebooks/x_monitor/x_monitor_healthcheck.py").read_text(
        encoding="utf-8"
    )

    assert "@app.function" in notebook_text
    assert '@flow(name="x-monitor-healthcheck"' in notebook_text
    assert 'mo.app_meta().mode == "edit"' in notebook_text
    assert 'mo.app_meta().mode == "script"' in notebook_text

from pathlib import Path


def test_financial_monitor_notebook_contains_required_flow_contract():
    notebook_text = Path(
        "notebooks/financial_monitor/financial_monitor_daily_pipeline.py"
    ).read_text(encoding="utf-8")

    assert notebook_text.index("@app.function") < notebook_text.index(
        '@flow(name="financial-monitor-daily-pipeline"'
    )
    assert "notify_on_failure" in notebook_text
    assert "with app.setup:" in notebook_text
    assert "def load_financial_monitor_config(" in notebook_text
    assert "def resolve_runtime_paths(" in notebook_text
    assert "def fetch_tdnet_candidates(" in notebook_text
    assert "def fetch_edinet_candidates(" in notebook_text
    assert "def download_source_documents(" in notebook_text
    assert "def extract_cash_metrics(" in notebook_text
    assert "def compute_cash_runway(" in notebook_text
    assert "def flag_management_intent(" in notebook_text
    assert "def persist_financial_snapshot(" in notebook_text
    assert "def write_financial_monitor_artifacts(" in notebook_text
    assert "create_markdown_artifact" in notebook_text
    assert 'mo.app_meta().mode == "edit"' in notebook_text
    assert 'mo.app_meta().mode == "script"' in notebook_text


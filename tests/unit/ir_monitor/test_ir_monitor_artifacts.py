from pathlib import Path

from src.services.ir_monitor.ir_monitor_artifacts import write_run_artifacts


def test_write_run_artifacts_creates_company_grouped_outputs(tmp_path: Path):
    artifact_paths = write_run_artifacts(
        workspace_dir=tmp_path,
        raw_report="raw",
        parsed_events=[
            {
                "company_id": "mitsubishi_corp",
                "company_name": "Mitsubishi Corporation",
                "ticker": "8058.T",
                "target_id": "mitsubishi_corp_ir_ja",
                "page_label": "Japanese IR page",
                "status": "changed",
                "diff_mode": "additions_only",
                "added_lines": ["ITEM_KEY=https://example.com/1 | DATE=2026-03-19 | TITLE=Notice"],
            },
            {
                "company_id": "nagase",
                "company_name": "NAGASE & Co., Ltd.",
                "ticker": "",
                "target_id": "nagase_ir_en",
                "page_label": "English IR page",
                "status": "baseline_initialized",
                "diff_mode": "additions_only",
                "added_lines": [],
            },
        ],
        run_label="2026-03-24T10-00-00+09-00",
    )

    markdown = artifact_paths.changes_markdown_path.read_text(encoding="utf-8")

    assert artifact_paths.raw_report_path.exists()
    assert artifact_paths.changes_json_path.exists()
    assert artifact_paths.changes_markdown_path.exists()
    assert "## Mitsubishi Corporation (8058.T)" in markdown
    assert "## NAGASE & Co., Ltd." in markdown
    assert "## NAGASE & Co., Ltd. (" not in markdown
    assert "baseline_initialized" in markdown

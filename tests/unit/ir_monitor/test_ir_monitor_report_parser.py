from pathlib import Path

from src.services.ir_monitor.ir_monitor_report_parser import parse_monitor_report


def test_parse_monitor_report_prefers_structured_changed_jobs_payload():
    raw_report = Path("tests/fixtures/ir_monitor/reports/webchanges_changed.txt").read_text(
        encoding="utf-8"
    )
    changed_jobs_payload = Path(
        "tests/fixtures/ir_monitor/reports/webchanges_changed_jobs.json"
    ).read_text(encoding="utf-8")

    parsed = parse_monitor_report(
        raw_report=raw_report,
        changed_jobs_payload=changed_jobs_payload,
        enabled_target_ids=["mitsubishi_corp_ir_ja", "nagase_ir_en"],
        baseline_target_ids=[],
        target_metadata_by_id={
            "mitsubishi_corp_ir_ja": {
                "company_id": "mitsubishi_corp",
                "company_name": "Mitsubishi Corporation",
                "page_label": "Japanese IR page",
                "diff_mode": "additions_only",
            },
            "nagase_ir_en": {
                "company_id": "nagase",
                "company_name": "NAGASE & Co., Ltd.",
                "page_label": "English IR page",
                "diff_mode": "additions_only",
            },
        },
    )

    assert parsed.changed_count == 1
    assert parsed.events[0].status == "changed"
    assert parsed.events[0].company_id == "mitsubishi_corp"
    assert parsed.events[0].company_name == "Mitsubishi Corporation"
    assert parsed.events[0].page_label == "Japanese IR page"
    assert parsed.events[0].added_lines == [
        "ITEM_KEY=https://example.co.jp/jp/ir/files/notice-20260319.pdf | DATE=2026-03-19 | TITLE=適時開示資料 | URL=https://example.co.jp/jp/ir/files/notice-20260319.pdf | TYPE=pdf | LANG=ja"
    ]
    assert parsed.unchanged_target_ids == ["nagase_ir_en"]


def test_parse_monitor_report_ignores_invalid_sidecar_and_uses_stdout_data():
    raw_report = Path("tests/fixtures/ir_monitor/reports/webchanges_changed.txt").read_text(
        encoding="utf-8"
    )
    changed_jobs_payload = Path(
        "tests/fixtures/ir_monitor/reports/webchanges_report_env.json"
    ).read_text(encoding="utf-8")

    parsed = parse_monitor_report(
        raw_report=raw_report,
        changed_jobs_payload=changed_jobs_payload,
        enabled_target_ids=["mitsubishi_corp_ir_ja"],
        baseline_target_ids=[],
        target_metadata_by_id={
            "mitsubishi_corp_ir_ja": {
                "company_id": "mitsubishi_corp",
                "company_name": "Mitsubishi Corporation",
                "page_label": "Japanese IR page",
                "diff_mode": "additions_only",
            }
        },
    )

    assert parsed.changed_count == 1
    assert parsed.events[0].target_id == "mitsubishi_corp_ir_ja"
    assert parsed.events[0].added_lines == [
        "ITEM_KEY=https://example.co.jp/jp/ir/files/notice-20260319.pdf | DATE=2026-03-19 | TITLE=適時開示資料 | URL=https://example.co.jp/jp/ir/files/notice-20260319.pdf | TYPE=pdf | LANG=ja"
    ]


def test_parse_monitor_report_falls_back_to_stdout_for_failures():
    raw_report = Path("tests/fixtures/ir_monitor/reports/webchanges_error.txt").read_text(
        encoding="utf-8"
    )

    parsed = parse_monitor_report(
        raw_report=raw_report,
        changed_jobs_payload=None,
        enabled_target_ids=["mitsubishi_corp_ir_ja"],
        baseline_target_ids=[],
        target_metadata_by_id={
            "mitsubishi_corp_ir_ja": {
                "company_id": "mitsubishi_corp",
                "company_name": "Mitsubishi Corporation",
                "page_label": "Japanese IR page",
                "diff_mode": "additions_only",
            }
        },
    )

    assert parsed.changed_count == 0
    assert parsed.events[0].status == "failed"
    assert parsed.events[0].page_label == "Japanese IR page"
    assert "timed out" in parsed.events[0].error_message

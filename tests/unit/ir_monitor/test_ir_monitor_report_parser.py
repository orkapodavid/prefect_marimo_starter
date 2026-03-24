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
    )

    assert parsed.changed_count == 1
    assert parsed.events[0].status == "changed"
    assert parsed.events[0].company_id == "mitsubishi_corp"
    assert parsed.unchanged_target_ids == ["nagase_ir_en"]


def test_parse_monitor_report_falls_back_to_stdout_for_failures():
    raw_report = Path("tests/fixtures/ir_monitor/reports/webchanges_error.txt").read_text(
        encoding="utf-8"
    )

    parsed = parse_monitor_report(
        raw_report=raw_report,
        changed_jobs_payload=None,
        enabled_target_ids=["mitsubishi_corp_ir_ja"],
        baseline_target_ids=[],
    )

    assert parsed.changed_count == 0
    assert parsed.events[0].status == "failed"
    assert "timed out" in parsed.events[0].error_message

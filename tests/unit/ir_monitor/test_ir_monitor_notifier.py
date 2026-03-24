import requests

from src.services.ir_monitor.ir_monitor_notifier import notify_if_needed


def test_notify_if_needed_skips_baseline_only_runs():
    result = notify_if_needed(
        parsed_events=[
            {
                "company_id": "nagase",
                "company_name": "NAGASE & Co., Ltd.",
                "target_id": "nagase_ir_en",
                "page_label": "English IR page",
                "status": "baseline_initialized",
                "diff_mode": "additions_only",
                "added_lines": [],
            }
        ],
        environment="prod",
        run_label="2026-03-24T10-00-00+09-00",
        artifact_path="./artifacts/changes.md",
        webhook_url="",
        notify_on_no_change=False,
    )

    assert result.sent is False
    assert result.channel == "none"


def test_notify_if_needed_falls_back_to_log_only_without_webhook():
    result = notify_if_needed(
        parsed_events=[
            {
                "company_id": "mitsubishi_corp",
                "company_name": "Mitsubishi Corporation",
                "target_id": "mitsubishi_corp_ir_ja",
                "page_label": "Japanese IR page",
                "status": "changed",
                "diff_mode": "additions_only",
                "added_lines": ["ITEM_KEY=https://example.com/1 | DATE=2026-03-19 | TITLE=Notice"],
            }
        ],
        environment="prod",
        run_label="2026-03-24T10-00-00+09-00",
        artifact_path="./artifacts/changes.md",
        webhook_url="",
        notify_on_no_change=False,
    )

    assert result.sent is False
    assert result.channel == "log"


def test_notify_if_needed_falls_back_to_log_only_when_webhook_fails(mocker):
    mocker.patch(
        "src.services.ir_monitor.ir_monitor_notifier.requests.post",
        side_effect=requests.RequestException("boom"),
    )

    result = notify_if_needed(
        parsed_events=[
            {
                "company_id": "mitsubishi_corp",
                "company_name": "Mitsubishi Corporation",
                "target_id": "mitsubishi_corp_ir_ja",
                "page_label": "Japanese IR page",
                "status": "changed",
                "diff_mode": "additions_only",
                "added_lines": ["ITEM_KEY=https://example.com/1 | DATE=2026-03-19 | TITLE=Notice"],
            }
        ],
        environment="prod",
        run_label="2026-03-24T10-00-00+09-00",
        artifact_path="./artifacts/changes.md",
        webhook_url="https://example.com/webhook",
        notify_on_no_change=False,
    )

    assert result.sent is False
    assert result.channel == "log"

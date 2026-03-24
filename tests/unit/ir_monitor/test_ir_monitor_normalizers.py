from pathlib import Path

from src.services.ir_monitor.normalizers.ir_monitor_generic_en_ir_news import (
    normalize as normalize_en,
)
from src.services.ir_monitor.normalizers.ir_monitor_generic_jp_ir_news import (
    normalize as normalize_jp,
)
from src.services.ir_monitor.normalizers.ir_monitor_generic_json_ir_feed import (
    normalize as normalize_json,
)


def test_generic_jp_ir_news_normalizes_to_stable_sorted_lines():
    html = Path("tests/fixtures/ir_monitor/html/jp_ir_list.html").read_text(encoding="utf-8")
    output = normalize_jp(html, "https://example.co.jp/jp/ir/")

    lines = output.splitlines()

    assert lines == sorted(lines)
    assert lines[0].startswith("ITEM_KEY=")
    assert "DATE=2026-03-19" in output
    assert "TYPE=pdf | LANG=ja" in output


def test_generic_en_ir_news_normalizes_to_stable_sorted_lines():
    html = Path("tests/fixtures/ir_monitor/html/en_ir_list.html").read_text(encoding="utf-8")
    output = normalize_en(html, "https://example.com/en/ir/")

    lines = output.splitlines()

    assert lines == sorted(lines)
    assert "DATE=2026-03-19" in output
    assert "LANG=en" in output


def test_generic_json_ir_feed_normalizes_to_stable_sorted_lines():
    payload = Path("tests/fixtures/ir_monitor/json/ir_feed.json").read_text(encoding="utf-8")
    output = normalize_json(payload, "https://example.com/api/ir/feed.json")

    lines = output.splitlines()

    assert lines == sorted(lines)
    assert "ITEM_KEY=https://example.com/api/ir/quarterly-results-20260319.pdf" in output
    assert "TYPE=json | LANG=ja" in output

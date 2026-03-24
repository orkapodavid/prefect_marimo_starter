from src.services.ir_monitor.ir_monitor_dates import normalize_date_text


def test_normalize_japanese_date():
    assert normalize_date_text("2026年3月19日") == "2026-03-19"


def test_normalize_english_date():
    assert normalize_date_text("Mar 19, 2026") == "2026-03-19"

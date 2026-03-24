from src.services.x_monitor.x_monitor_text_normalizer import normalize_post_text


def test_normalize_removes_zero_width_and_collapses_whitespace():
    assert normalize_post_text("Earn\u200bings   launch") == "earnings launch"


def test_normalize_applies_nfkc():
    assert normalize_post_text("ﬁnance") == "finance"


def test_normalize_strips_control_chars():
    assert normalize_post_text("hello\x00world") == "hello world"


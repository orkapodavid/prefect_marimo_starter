from src.services.ir_monitor.ir_monitor_urls import to_absolute_url


def test_to_absolute_url_trims_whitespace():
    assert (
        to_absolute_url(" /jp/ir/notice.pdf ", "https://example.co.jp/jp/ir/")
        == "https://example.co.jp/jp/ir/notice.pdf"
    )

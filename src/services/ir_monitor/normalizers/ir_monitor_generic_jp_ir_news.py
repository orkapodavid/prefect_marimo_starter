"""Normalize Japanese IR news pages into stable lines."""

from services.ir_monitor.normalizers.ir_monitor_html_news_common import normalize_html_news


def normalize(content: str, page_url: str) -> str:
    """Normalize a Japanese IR listing page into sorted item lines."""
    return normalize_html_news(content, page_url, lang="ja")

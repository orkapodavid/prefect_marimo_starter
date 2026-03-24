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


def test_generic_en_ir_news_filters_noise_deduplicates_and_extracts_dates():
    html = """
    <html>
      <body>
        <nav>
          <a href="/about/">About</a>
          <a href="https://instagram.com/example">Instagram</a>
        </nav>
        <div class="news-card">
          <a href="/news/quarterly-results/"><img alt="" /></a>
          <div class="news-card__date">
            <span class="news-card__date-month">March 31</span>
            <span class="news-card__date-year">2025</span>
          </div>
          <h2><a href="/news/quarterly-results/">Quarterly Results</a></h2>
        </div>
        <div class="news-card">
          <a href="/news/notice-20260319.pdf"></a>
          <div class="news-card__date">Mar 19, 2026</div>
          <h2><a href="/news/notice-20260319.pdf">Notice PDF</a></h2>
        </div>
        <footer>
          <a href="/contact/">Contact</a>
        </footer>
      </body>
    </html>
    """

    output = normalize_en(html, "https://example.com/news/")

    assert output.splitlines() == [
        "ITEM_KEY=https://example.com/news/notice-20260319.pdf | DATE=2026-03-19 | TITLE=Notice PDF | URL=https://example.com/news/notice-20260319.pdf | TYPE=pdf | LANG=en",
        "ITEM_KEY=https://example.com/news/quarterly-results/ | DATE=2025-03-31 | TITLE=Quarterly Results | URL=https://example.com/news/quarterly-results/ | TYPE=html | LANG=en",
    ]


def test_generic_jp_ir_news_filters_noise_deduplicates_and_extracts_dates():
    html = """
    <html>
      <body>
        <nav>
          <a href="/company/">会社情報</a>
        </nav>
        <ul>
          <li class="news-item">
            <a href="/ir/notice-20260319.pdf"><img alt="" /></a>
            <span class="news-item__date">2026年3月19日</span>
            <a href="/ir/notice-20260319.pdf">適時開示資料</a>
          </li>
          <li class="news-item">
            <a href="/ir/results-20260301/"></a>
            <div class="news-item__date-wrapper">
              <span class="news-item__date-month">2026年3月1日</span>
            </div>
            <a href="/ir/results-20260301/">決算短信</a>
          </li>
        </ul>
        <footer>
          <a href="/privacy/">プライバシー</a>
        </footer>
      </body>
    </html>
    """

    output = normalize_jp(html, "https://example.co.jp/ir/")

    assert output.splitlines() == [
        "ITEM_KEY=https://example.co.jp/ir/notice-20260319.pdf | DATE=2026-03-19 | TITLE=適時開示資料 | URL=https://example.co.jp/ir/notice-20260319.pdf | TYPE=pdf | LANG=ja",
        "ITEM_KEY=https://example.co.jp/ir/results-20260301/ | DATE=2026-03-01 | TITLE=決算短信 | URL=https://example.co.jp/ir/results-20260301/ | TYPE=html | LANG=ja",
    ]

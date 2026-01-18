"""
TDnet Test Fixtures
===================

Shared pytest fixtures for TDnet scraper tests.
"""

import pytest
from datetime import date


@pytest.fixture
def sample_search_html():
    """Sample HTML response from tdnet-search.appspot.com."""
    return """
    <html><body><table>
    <tr>
        <td>2025/01/01 10:00</td>
        <td>12340</td>
        <td>Test Company</td>
        <td><a href="test.pdf">Test Title</a></td>
    </tr>
    <tr>
        <td colspan="4">Test Description</td>
    </tr>
    </table></body></html>
    """


@pytest.fixture
def sample_deal_text():
    """Sample Japanese text for deal details extraction tests."""
    return """
    割当先：Test Investor
    調達資金：100,000,000円
    発行価額：1,000円
    発行新株式数：100,000株
    払込期日：2025年1月1日
    新株式発行
    """


@pytest.fixture
def sample_warrant_text():
    """Sample Japanese text for warrant deal extraction tests."""
    return """
    1. 割当先：株式会社テスト投資
    2. 調達資金の額：500,000,000円
    3. 発行価額：1,000円
    4. 発行新株式数：500,000株
    5. 払込期日：2026年1月15日
    6. 本件は新株予約権の発行です。
    """


@pytest.fixture
def sample_announcement_html():
    """Sample HTML response from TDnet announcements."""
    return """
    <html>
    <body>
    <div>Total 5 Announcements</div>
    <table>
        <tr>
            <td>2026/01/15 16:30</td>
            <td>40620</td>
            <td><a href="/pdf?doc=12345">Sample Announcement Title</a></td>
            <td>Technology</td>
            <td>Sample Company Ltd</td>
            <td></td>
        </tr>
    </table>
    </body>
    </html>
    """


@pytest.fixture
def sample_japanese_announcement_html():
    """Sample HTML response from Japanese TDnet."""
    return """
    <html>
    <head><meta charset="utf-8"></head>
    <body>
    <table>
        <tr>
            <td>16:30</td>
            <td>40620</td>
            <td>東</td>
            <td>サンプル会社株式会社</td>
            <td><a href="/pdf?doc=12345">サンプルお知らせ</a></td>
            <td></td>
        </tr>
    </table>
    </body>
    </html>
    """


@pytest.fixture
def test_date_today():
    """Return today's date for tests."""
    return date.today()


@pytest.fixture
def test_date_range():
    """Return a common date range tuple for tests."""
    return (date(2025, 1, 1), date(2025, 1, 31))

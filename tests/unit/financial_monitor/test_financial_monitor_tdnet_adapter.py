from datetime import date

from services.financial_monitor.financial_monitor_models import FinancialMonitorTarget
from services.financial_monitor.financial_monitor_tdnet_adapter import fetch_tdnet_candidates
from services.tdnet.tdnet_announcement_models import TdnetAnnouncement, TdnetLanguage, TdnetScrapeResult


def test_tdnet_adapter_filters_to_cash_relevant_titles(tdnet_scrape_result, monkeypatch):
    target = FinancialMonitorTarget(
        id="mitsubishi_corp_results",
        company_id="mitsubishi_corp",
        company_name="Mitsubishi Corporation",
        ticker="8058.T",
        exchange="TSE",
        edinet_code="E02529",
        tdnet_language="japanese",
        disclosure_keywords=["決算短信", "資金の借入"],
        include_edinet=True,
        enabled=True,
    )

    def fake_scrape_announcements(start_date, end_date, query="", delay=1.0, language=None):
        assert start_date == date(2026, 3, 25)
        assert end_date == date(2026, 3, 25)
        assert query == ""
        assert delay == 1.0
        assert language == TdnetLanguage.JAPANESE
        return tdnet_scrape_result

    monkeypatch.setattr(
        "services.financial_monitor.financial_monitor_tdnet_adapter.scrape_announcements",
        fake_scrape_announcements,
    )

    candidates = fetch_tdnet_candidates(targets=[target], filing_date=date(2026, 3, 25))

    assert [candidate.title for candidate in candidates] == [
        "2026年3月期 第3四半期決算短信〔IFRS〕（連結）",
        "資金の借入に関するお知らせ",
    ]
    assert candidates[0].company_code == "8058"
    assert candidates[0].disclosure_date == date(2026, 3, 25)
    assert candidates[0].source_url == "https://tdnet.example/8058-results.pdf"


def test_tdnet_adapter_matches_tdnet_five_digit_stock_codes(monkeypatch):
    target = FinancialMonitorTarget(
        id="max_results",
        company_id="max",
        company_name="Max Co., Ltd.",
        ticker="6454.T",
        exchange="TSE",
        edinet_code="E02381",
        tdnet_language="japanese",
        disclosure_keywords=["決算短信"],
        include_edinet=True,
        enabled=True,
    )

    scrape_result = TdnetScrapeResult(
        start_date=date(2026, 3, 25),
        end_date=date(2026, 3, 25),
        total_count=1,
        page_count=1,
        language=TdnetLanguage.JAPANESE,
        announcements=[
            TdnetAnnouncement(
                publish_datetime="2026-03-25T15:30:00",
                publish_date="2026-03-25",
                stock_code="64540",
                company_name="マックス",
                title="（訂正・数値データ訂正）「2026年3月期 第2四半期（中間期）決算短信〔日本基準〕（連結）」の一部訂正について",
                pdf_url="https://tdnet.example/64540-results.pdf",
                has_xbrl=True,
                language=TdnetLanguage.JAPANESE,
                xbrl_url="https://tdnet.example/64540-results.zip",
            )
        ],
    )

    def fake_scrape_announcements(start_date, end_date, query="", delay=1.0, language=None):
        return scrape_result

    monkeypatch.setattr(
        "services.financial_monitor.financial_monitor_tdnet_adapter.scrape_announcements",
        fake_scrape_announcements,
    )

    candidates = fetch_tdnet_candidates(targets=[target], filing_date=date(2026, 3, 25))

    assert [candidate.company_code for candidate in candidates] == ["64540"]

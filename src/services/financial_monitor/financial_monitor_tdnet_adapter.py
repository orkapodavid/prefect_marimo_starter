"""Adapter helpers for reusing TDnet announcement discovery."""

from collections import defaultdict
from datetime import date

from services.financial_monitor.financial_monitor_models import (
    FinancialMonitorTarget,
    FinancialMonitorTdnetCandidate,
)
from services.tdnet.tdnet_announcement_models import TdnetAnnouncement, TdnetLanguage
from services.tdnet.tdnet_announcement_scraper import scrape_announcements


def _normalize_tdnet_company_code(value: str) -> str:
    company_code = value.split(".", 1)[0].strip()
    if company_code.isdigit() and len(company_code) == 4:
        return f"{company_code}0"
    return company_code


def _title_matches_keywords(title: str, keywords: list[str]) -> bool:
    normalized_title = title.lower()
    return any(keyword.lower() in normalized_title for keyword in keywords)


def _announcement_matches_target(
    announcement: TdnetAnnouncement,
    target: FinancialMonitorTarget,
) -> bool:
    return (
        _normalize_tdnet_company_code(target.ticker)
        == _normalize_tdnet_company_code(announcement.stock_code)
        and _title_matches_keywords(announcement.title, target.disclosure_keywords)
    )


def _build_tdnet_candidate(
    target: FinancialMonitorTarget,
    announcement: TdnetAnnouncement,
) -> FinancialMonitorTdnetCandidate:
    return FinancialMonitorTdnetCandidate(
        target_id=target.id,
        company_id=target.company_id,
        company_name=target.company_name,
        company_code=announcement.stock_code,
        ticker=target.ticker,
        exchange=target.exchange,
        edinet_code=target.edinet_code,
        title=announcement.title,
        disclosure_date=announcement.publish_date,
        source_url=announcement.pdf_url or announcement.xbrl_url or "",
        pdf_url=announcement.pdf_url,
        xbrl_url=announcement.xbrl_url,
        has_xbrl=announcement.has_xbrl,
    )


def fetch_tdnet_candidates(
    targets: list[FinancialMonitorTarget],
    filing_date: date,
    delay: float = 1.0,
) -> list[FinancialMonitorTdnetCandidate]:
    """Fetch TDnet announcements and filter them to configured cash-relevant targets."""
    targets_by_language: dict[str, list[FinancialMonitorTarget]] = defaultdict(list)
    for target in targets:
        if target.enabled:
            targets_by_language[target.tdnet_language].append(target)

    candidates: list[FinancialMonitorTdnetCandidate] = []
    for language, language_targets in targets_by_language.items():
        scrape_result = scrape_announcements(
            filing_date,
            filing_date,
            delay=delay,
            language=TdnetLanguage(language),
        )
        for announcement in scrape_result.announcements:
            for target in language_targets:
                if _announcement_matches_target(announcement, target):
                    candidates.append(_build_tdnet_candidate(target, announcement))

    return candidates

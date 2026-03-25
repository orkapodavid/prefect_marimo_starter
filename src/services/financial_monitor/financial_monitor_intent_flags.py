"""Deterministic intent-flag rules for financial monitor."""

from services.financial_monitor.financial_monitor_models import FinancialMonitorIntentSignalRecord

INTENT_RULES = [
    {
        "signal_type": "fundraising",
        "phrase": "第三者割当",
        "match_rule": "phrase:fundraising:third_party_allotment",
    },
    {
        "signal_type": "fundraising",
        "phrase": "借入",
        "match_rule": "phrase:fundraising:borrowing",
    },
    {
        "signal_type": "liquidity",
        "phrase": "手元流動性",
        "match_rule": "phrase:liquidity:on_hand_liquidity",
    },
    {
        "signal_type": "liquidity",
        "phrase": "資金繰り",
        "match_rule": "phrase:liquidity:cash_management",
    },
]


def _build_excerpt(text: str, phrase: str, window: int = 30) -> str:
    start = max(text.find(phrase) - window, 0)
    end = min(text.find(phrase) + len(phrase) + window, len(text))
    return text[start:end].strip()


def flag_management_intent(
    text: str,
    source_section: str = "management_commentary",
) -> list[FinancialMonitorIntentSignalRecord]:
    """Apply deterministic phrase rules to a management-text block."""
    signals: list[FinancialMonitorIntentSignalRecord] = []
    for rule in INTENT_RULES:
        if rule["phrase"] in text:
            signals.append(
                FinancialMonitorIntentSignalRecord(
                    signal_type=rule["signal_type"],
                    matched_phrase=rule["phrase"],
                    excerpt=_build_excerpt(text, rule["phrase"]),
                    source_section=source_section,
                    match_rule=rule["match_rule"],
                )
            )
    return signals

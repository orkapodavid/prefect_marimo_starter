from services.financial_monitor.financial_monitor_intent_flags import flag_management_intent


def test_flag_management_intent_returns_reason_codes_for_capital_raising_phrases():
    text = "当社は第三者割当による資金調達を実施し、手元流動性を確保します。"

    signals = flag_management_intent(text=text, source_section="management_commentary")

    assert len(signals) == 2
    assert signals[0].signal_type == "fundraising"
    assert signals[0].matched_phrase == "第三者割当"
    assert signals[0].match_rule == "phrase:fundraising:third_party_allotment"
    assert signals[1].signal_type == "liquidity"
    assert signals[1].match_rule == "phrase:liquidity:on_hand_liquidity"


from services.financial_monitor.financial_monitor_cash_metrics import (
    compute_cash_runway,
    compute_monthly_burn,
)


def test_compute_cash_runway_returns_none_when_inputs_are_incomplete():
    assert compute_cash_runway(cash=None, monthly_burn=100) is None
    assert compute_cash_runway(cash=1200, monthly_burn=None) is None
    assert compute_cash_runway(cash=1200, monthly_burn=0) is None


def test_compute_cash_runway_returns_expected_months():
    assert compute_cash_runway(cash=1200, monthly_burn=100) == 12.0


def test_compute_monthly_burn_uses_negative_operating_cash_flow():
    assert compute_monthly_burn(operating_cash_flow=-1200, period_months=12) == 100.0
    assert compute_monthly_burn(operating_cash_flow=500, period_months=12) is None


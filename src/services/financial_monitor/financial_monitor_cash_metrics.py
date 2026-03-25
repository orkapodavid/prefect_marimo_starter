"""Deterministic cash-metric helpers for financial monitor."""


def compute_monthly_burn(
    operating_cash_flow: float | None,
    period_months: int = 12,
) -> float | None:
    """Compute monthly burn from operating cash flow when it is negative."""
    if operating_cash_flow is None or period_months <= 0:
        return None
    if operating_cash_flow >= 0:
        return None
    return round(abs(operating_cash_flow) / period_months, 2)


def compute_cash_runway(
    cash: float | None,
    monthly_burn: float | None,
) -> float | None:
    """Compute cash runway in months when both inputs are available."""
    if cash is None or monthly_burn is None or monthly_burn <= 0:
        return None
    return round(cash / monthly_burn, 2)

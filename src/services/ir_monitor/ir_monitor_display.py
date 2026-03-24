"""Shared display formatting helpers for IR monitor output."""


def company_display_name(company_name: str, ticker: str = "") -> str:
    """Render a company label with an optional ticker suffix."""
    if ticker:
        return f"{company_name} ({ticker})"
    return company_name

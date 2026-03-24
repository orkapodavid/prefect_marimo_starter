"""Shared display formatting helpers for IR monitor output."""


def company_display_name(company_name: str, ticker: str = "") -> str:
    """Render a company label with an optional ticker suffix."""
    if ticker:
        return f"{company_name} ({ticker})"
    return company_name


def group_events_by_company(parsed_events: list[dict]) -> dict[str, list[dict]]:
    """Group events by their user-facing company label."""
    grouped_events: dict[str, list[dict]] = {}
    for event in parsed_events:
        grouped_events.setdefault(
            company_display_name(event["company_name"], event.get("ticker", "")),
            [],
        ).append(event)
    return grouped_events

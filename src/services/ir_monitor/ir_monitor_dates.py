"""Date normalization helpers for IR monitor content."""

from datetime import datetime
import re


def normalize_date_text(value: str) -> str | None:
    """Normalize common Japanese and English date strings to YYYY-MM-DD."""
    cleaned_value = value.strip()
    if not cleaned_value:
        return None

    japanese_match = re.fullmatch(r"(\d{4})年(\d{1,2})月(\d{1,2})日", cleaned_value)
    if japanese_match:
        year, month, day = (int(part) for part in japanese_match.groups())
        return f"{year:04d}-{month:02d}-{day:02d}"

    for pattern in ("%Y/%m/%d", "%Y-%m-%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(cleaned_value, pattern).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None

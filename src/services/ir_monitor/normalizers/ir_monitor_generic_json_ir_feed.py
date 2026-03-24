"""Normalize JSON IR feeds into stable lines."""

import json

from services.ir_monitor.ir_monitor_dates import normalize_date_text
from services.ir_monitor.ir_monitor_urls import to_absolute_url


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def normalize(content: str, page_url: str) -> str:
    """Normalize a JSON IR feed into sorted item lines."""
    payload = json.loads(content)
    items = payload if isinstance(payload, list) else payload.get("items", [])
    normalized_lines: list[str] = []

    for item in items:
        absolute_url = to_absolute_url(item["url"], page_url)
        date_value = normalize_date_text(_clean_text(item.get("date", ""))) or ""
        title = _clean_text(item.get("title", ""))
        item_type = item.get("type", "json")
        language = item.get("language", "ja")
        normalized_lines.append(
            " | ".join(
                [
                    f"ITEM_KEY={absolute_url}",
                    f"DATE={date_value}",
                    f"TITLE={title}",
                    f"URL={absolute_url}",
                    f"TYPE={item_type}",
                    f"LANG={language}",
                ]
            )
        )

    return "\n".join(sorted(normalized_lines))

"""Normalize Japanese IR news pages into stable lines."""

from bs4 import BeautifulSoup

from services.ir_monitor.ir_monitor_dates import normalize_date_text
from services.ir_monitor.ir_monitor_urls import to_absolute_url


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _infer_item_type(url: str) -> str:
    lowered_url = url.lower()
    if lowered_url.endswith(".pdf"):
        return "pdf"
    if lowered_url.endswith(".json"):
        return "json"
    return "html"


def normalize(content: str, page_url: str) -> str:
    """Normalize a Japanese IR listing page into sorted item lines."""
    soup = BeautifulSoup(content, "lxml")
    normalized_lines: list[str] = []

    for link in soup.find_all("a", href=True):
        container = link.find_parent(["li", "article", "div"]) or link.parent
        date_value = ""
        if container is not None:
            date_node = container.find(["time", "span"], class_="date") or container.find("time")
            if date_node is not None:
                date_value = normalize_date_text(_clean_text(date_node.get_text())) or ""

        absolute_url = to_absolute_url(link["href"], page_url)
        title = _clean_text(link.get_text())
        item_type = _infer_item_type(absolute_url)
        normalized_lines.append(
            " | ".join(
                [
                    f"ITEM_KEY={absolute_url}",
                    f"DATE={date_value}",
                    f"TITLE={title}",
                    f"URL={absolute_url}",
                    f"TYPE={item_type}",
                    "LANG=ja",
                ]
            )
        )

    return "\n".join(sorted(normalized_lines))

"""Shared helpers for HTML IR/news list normalizers."""

from collections import Counter
from typing import Any
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Tag

from services.ir_monitor.ir_monitor_dates import normalize_date_text
from services.ir_monitor.ir_monitor_urls import to_absolute_url

_DATE_CLASS_TOKENS = ("date", "time", "day", "month", "year", "posted", "publish")
_CONTAINER_TAGS = ("article", "li", "div")


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _infer_item_type(url: str) -> str:
    lowered_url = url.lower()
    if lowered_url.endswith(".pdf"):
        return "pdf"
    if lowered_url.endswith(".json"):
        return "json"
    return "html"


def _normalized_host(value: str) -> str:
    return urlsplit(value).netloc.lower().removeprefix("www.")


def _is_relevant_url(absolute_url: str, page_url: str) -> bool:
    lowered_url = absolute_url.lower()
    if lowered_url.startswith(("javascript:", "mailto:", "tel:")):
        return False

    item_type = _infer_item_type(absolute_url)
    if item_type in {"pdf", "json"}:
        return True

    return _normalized_host(absolute_url) == _normalized_host(page_url)


def _container_signature(container: Tag) -> str:
    classes = ".".join(sorted(container.get("class", [])))
    return f"{container.name}.{classes}" if classes else container.name


def _date_class_matcher(value: Any) -> bool:
    if not value:
        return False
    values = value if isinstance(value, list) else [value]
    flattened = " ".join(str(item) for item in values).lower()
    return any(token in flattened for token in _DATE_CLASS_TOKENS)


def _extract_date(container: Tag) -> str:
    candidate_texts: list[str] = []

    for node in container.find_all("time"):
        text = _clean_text(node.get_text(" ", strip=True))
        if text:
            candidate_texts.append(text)

    for node in container.find_all(class_=_date_class_matcher):
        text = _clean_text(node.get_text(" ", strip=True))
        if text:
            candidate_texts.append(text)

    unique_texts = list(dict.fromkeys(candidate_texts))
    for text in unique_texts:
        normalized = normalize_date_text(text)
        if normalized:
            return normalized

    combined = _clean_text(" ".join(unique_texts))
    if combined:
        normalized = normalize_date_text(combined)
        if normalized:
            return normalized

    if len(unique_texts) >= 2:
        for first, second in zip(unique_texts, unique_texts[1:]):
            normalized = normalize_date_text(f"{first}, {second}")
            if normalized:
                return normalized

    return ""


def _candidate_containers(soup: BeautifulSoup, page_url: str) -> list[tuple[Tag, str]]:
    containers: list[tuple[Tag, str, str]] = []
    signature_counts: Counter[str] = Counter()
    dated_signature_counts: Counter[str] = Counter()

    for container in soup.find_all(_CONTAINER_TAGS):
        if not container.get("class"):
            continue
        links = container.find_all("a", href=True)
        if not links:
            continue
        signature = _container_signature(container)
        date_value = _extract_date(container)
        has_relevant_link = any(
            _is_relevant_url(to_absolute_url(link["href"], page_url), page_url) for link in links
        )
        if not has_relevant_link:
            continue
        containers.append((container, signature, date_value))
        signature_counts[signature] += 1
        if date_value:
            dated_signature_counts[signature] += 1

    selected_signatures = {
        signature for signature, count in dated_signature_counts.items() if count >= 2
    }
    if not selected_signatures:
        selected_signatures = {
            signature for signature, count in signature_counts.items() if count >= 2
        }

    selected_containers: list[tuple[Tag, str]] = []
    for container, signature, date_value in containers:
        if signature not in selected_signatures:
            continue
        if container.find_parent(
            lambda tag: isinstance(tag, Tag) and _container_signature(tag) in selected_signatures
        ):
            continue
        selected_containers.append((container, date_value))

    return selected_containers


def _record_sort_key(record: dict[str, str]) -> tuple[int, int, int, int]:
    return (
        int(bool(record["date"])),
        int(bool(record["title"])),
        len(record["title"]),
        int(record["item_type"] != "html"),
    )


def normalize_html_news(content: str, page_url: str, lang: str) -> str:
    """Normalize an HTML news/IR listing page into stable item lines."""
    soup = BeautifulSoup(content, "lxml")
    containers = _candidate_containers(soup, page_url)
    if not containers:
        containers = []
        for link in soup.find_all("a", href=True):
            parent = link.find_parent(_CONTAINER_TAGS)
            if parent is None:
                continue
            containers.append((parent, _extract_date(parent)))

    best_records_by_key: dict[str, dict[str, str]] = {}
    for container, date_value in containers:
        for link in container.find_all("a", href=True):
            absolute_url = to_absolute_url(link["href"], page_url)
            if not _is_relevant_url(absolute_url, page_url):
                continue

            title = _clean_text(link.get_text(" ", strip=True))
            item_type = _infer_item_type(absolute_url)
            record = {
                "item_key": absolute_url,
                "date": date_value,
                "title": title,
                "url": absolute_url,
                "item_type": item_type,
                "lang": lang,
            }
            existing_record = best_records_by_key.get(absolute_url)
            if existing_record is None or _record_sort_key(record) > _record_sort_key(existing_record):
                best_records_by_key[absolute_url] = record

    normalized_lines = [
        " | ".join(
            [
                f"ITEM_KEY={record['item_key']}",
                f"DATE={record['date']}",
                f"TITLE={record['title']}",
                f"URL={record['url']}",
                f"TYPE={record['item_type']}",
                f"LANG={record['lang']}",
            ]
        )
        for record in best_records_by_key.values()
        if record["title"] or record["date"] or record["item_type"] != "html"
    ]
    return "\n".join(sorted(normalized_lines))

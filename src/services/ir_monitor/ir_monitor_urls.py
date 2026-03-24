"""URL helpers for the IR monitor feature."""

from urllib.parse import urljoin


def to_absolute_url(url: str, page_url: str) -> str:
    """Resolve a possibly relative URL against the page URL."""
    return urljoin(page_url, url.strip())

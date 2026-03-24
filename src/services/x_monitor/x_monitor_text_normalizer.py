"""Text normalization helpers for X monitor matching."""

import re
import unicodedata

ZERO_WIDTH_CHARS = {"\u200b", "\u200c", "\u200d", "\ufeff"}


def normalize_post_text(text: str) -> str:
    """Normalize post text for matching without mutating the rendered source."""
    normalized = unicodedata.normalize("NFKC", text).lower()

    cleaned_parts: list[str] = []
    for char in normalized:
        if char in ZERO_WIDTH_CHARS:
            continue
        if unicodedata.category(char).startswith("C"):
            cleaned_parts.append(" ")
        else:
            cleaned_parts.append(char)

    cleaned_text = "".join(cleaned_parts)
    return re.sub(r"\s+", " ", cleaned_text).strip()


"""Rule evaluation for X monitor targets."""

import re

from services.x_monitor.x_monitor_models import XMonitorMatchResult
from services.x_monitor.x_monitor_text_normalizer import normalize_post_text


def _normalized_terms(terms: list[str]) -> list[str]:
    return [normalize_post_text(term) for term in terms if term]


def evaluate_target_match(target: dict, post: dict) -> XMonitorMatchResult:
    """Evaluate a fetched post against a target's matching rules."""
    if post.get("is_retweet") and not target.get("include_retweets", False):
        return XMonitorMatchResult(matched=False, match_reason="retweets_disabled")

    if post.get("is_reply") and not target.get("include_replies", False):
        return XMonitorMatchResult(matched=False, match_reason="replies_disabled")

    if target.get("media_only") and not post.get("has_media"):
        return XMonitorMatchResult(matched=False, match_reason="media_required")

    normalized_text = normalize_post_text(post.get("text_raw", ""))
    matched_rules: list[str] = []

    keywords_any = _normalized_terms(target.get("keywords_any", []))
    if keywords_any:
        if not any(keyword in normalized_text for keyword in keywords_any):
            return XMonitorMatchResult(matched=False, match_reason="keywords_any_not_matched")
        matched_rules.append("keywords_any")

    keywords_all = _normalized_terms(target.get("keywords_all", []))
    if keywords_all:
        if not all(keyword in normalized_text for keyword in keywords_all):
            return XMonitorMatchResult(matched=False, match_reason="keywords_all_not_matched")
        matched_rules.append("keywords_all")

    regex_any = target.get("regex_any", [])
    if regex_any:
        if not any(re.search(pattern, normalized_text, flags=re.IGNORECASE) for pattern in regex_any):
            return XMonitorMatchResult(matched=False, match_reason="regex_any_not_matched")
        matched_rules.append("regex_any")

    if not keywords_any and not keywords_all and not regex_any:
        return XMonitorMatchResult(matched=True, match_reason="no_rules_defined")

    return XMonitorMatchResult(matched=True, matched_rules=matched_rules)

"""
TDnet Search Constants
======================

Constants for the TDnet Search Scraper service.

Documentation: docs/tdnet/TDNET_SEARCH_OPTIMIZATION.md

This module contains:
- Search endpoint URL
- Tiered search terms for third-party allotment detection
- Tier precision mappings
"""

# Base URL for TDnet Search API
BASE_URL = "https://tdnet-search.appspot.com/search"

# Tiered search terms for third-party allotment announcements
# Reference: docs/tdnet/TDNET_SEARCH_OPTIMIZATION.md
SEARCH_TERMS = {
    "tier1": [
        {
            "query": "第三者割当 発行に関するお知らせ",
            "precision": "95%+",
            "description": "Initial issuance announcements",
        },
        {
            "query": "第三者割当 募集に関するお知らせ",
            "precision": "95%+",
            "description": "Initial offering announcements",
        },
    ],
    "tier2": [
        {
            "query": "第三者割当 新株式 -払込完了",
            "precision": "90%+",
            "description": "Common stock issuances (excluding completions)",
        },
        {
            "query": "第三者割当 新株予約権 -払込完了",
            "precision": "90%+",
            "description": "Warrant issuances (excluding completions)",
        },
    ],
    "tier3": [
        {
            "query": "第三者割当 割当先決定",
            "precision": "85%+",
            "description": "Allottee decision announcements",
        },
    ],
}

# Human-readable tier labels
TIER_MAPPING = {
    "tier1": "Tier 1 (95%+)",
    "tier2": "Tier 2 (90%+)",
    "tier3": "Tier 3 (85%+)",
}

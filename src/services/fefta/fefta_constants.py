"""
FEFTA Crawler Constants
=======================

Constants used by the FEFTA crawler service.
"""

from pathlib import Path

DEFAULT_BASE_URL = (
    "https://www.mof.go.jp/english/policy/international_policy/fdi/"
    "Related_Guidance_and_Documents/index.html"
)

# User-Agent header for requests
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Default output directory (relative to project root)
DEFAULT_OUTPUT_DIR = Path("data/output/fefta")

# Month name to number mapping (case-insensitive)
MONTH_MAP = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    # Abbreviations
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

# Circled numerals to integer mapping
CIRCLED_NUMERAL_MAP = {
    "①": 1,
    "②": 2,
    "③": 3,
    "④": 4,
    "⑤": 5,
    "⑥": 6,
    "⑦": 7,
    "⑧": 8,
    "⑨": 9,
    "⑩": 10,
}

# Expected sheet name in the Excel file
SHEET_NAME = "上場企業の該当性リスト"

# Column name mappings (substring matching for robustness)
COLUMN_MAPPINGS = {
    "securities_code": ["証券コード", "Securities code"],
    "isin_code": ["ISINコード", "ISIN code"],
    "company_name_ja": ["会社名（和名）", "会社名"],
    "issue_or_company_name": ["Issue name", "company name"],
    "category": ["区分"],
    "core_operator": ["特定コア事業者"],
}

"""
FEFTA Helper Functions Unit Tests
==================================

Unit tests for the FEFTA helper functions.
These tests do not require network access.

Run with: pytest tests/unit/fefta/test_fefta_helpers.py -v
"""

import pytest
from datetime import date

from src.services.fefta.fefta_helpers import (
    parse_as_of_date,
    find_fefta_links,
    normalize_circled_numeral,
    normalize_circled_numeral_optional,
    map_columns,
)
from src.services.fefta.fefta_models import (
    FeftaDateParseError,
    FeftaExcelParseError,
)
from bs4 import BeautifulSoup


# =============================================================================
# Test: parse_as_of_date
# =============================================================================


class TestParseAsOfDate:
    """Test the 'As of' date parsing functionality."""

    def test_parse_standard_format(self):
        """Test parsing standard date format: 'As of 15 July, 2025'."""
        link_text = 'the "List of classifications..." FEFTA (As of 15 July, 2025)(Excel:296KB)'
        as_of_raw, as_of_date = parse_as_of_date(link_text)

        assert as_of_raw == "As of 15 July, 2025"
        assert as_of_date == date(2025, 7, 15)

    def test_parse_without_comma(self):
        """Test parsing date without comma: 'As of 15 July 2025'."""
        link_text = "FEFTA (As of 1 January 2026)(Excel:100KB)"
        as_of_raw, as_of_date = parse_as_of_date(link_text)

        assert as_of_date == date(2026, 1, 1)

    def test_parse_abbreviated_month(self):
        """Test parsing abbreviated month names."""
        link_text = "FEFTA document (As of 5 Jan, 2025)"
        as_of_raw, as_of_date = parse_as_of_date(link_text)

        assert as_of_date == date(2025, 1, 5)

    def test_parse_all_months(self):
        """Test parsing all month names."""
        months = [
            ("January", 1),
            ("February", 2),
            ("March", 3),
            ("April", 4),
            ("May", 5),
            ("June", 6),
            ("July", 7),
            ("August", 8),
            ("September", 9),
            ("October", 10),
            ("November", 11),
            ("December", 12),
        ]
        for month_name, month_num in months:
            link_text = f"FEFTA (As of 15 {month_name}, 2025)"
            _, as_of_date = parse_as_of_date(link_text)
            assert as_of_date.month == month_num

    def test_invalid_raises_error(self):
        """Test that invalid date format raises FeftaDateParseError."""
        link_text = "FEFTA document without date"

        with pytest.raises(FeftaDateParseError):
            parse_as_of_date(link_text)

    def test_invalid_month_raises_error(self):
        """Test that unknown month name raises FeftaDateParseError."""
        link_text = "FEFTA (As of 15 Smarch, 2025)"

        with pytest.raises(FeftaDateParseError):
            parse_as_of_date(link_text)


# =============================================================================
# Test: find_fefta_links
# =============================================================================


class TestFindFeftaLinks:
    """Test the FEFTA link finding functionality."""

    def test_find_single_link(self):
        """Test finding a single FEFTA link."""
        html = """
        <html>
            <body>
                <a href="gaitouseilist20250715.xlsx">FEFTA List (As of 15 July, 2025)</a>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        links = find_fefta_links(soup, "https://example.com/")

        assert len(links) == 1
        assert links[0]["file_url"] == "https://example.com/gaitouseilist20250715.xlsx"
        assert links[0]["as_of_date"] == date(2025, 7, 15)

    def test_find_multiple_links_sorted_by_date(self):
        """Test finding multiple links and selecting latest."""
        html = """
        <html>
            <body>
                <a href="old.xlsx">FEFTA List (As of 1 January, 2024)</a>
                <a href="new.xlsx">FEFTA List (As of 15 July, 2025)</a>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        links = find_fefta_links(soup, "https://example.com/")

        assert len(links) == 2
        # Latest date should be the max
        latest = max(links, key=lambda x: x["as_of_date"])
        assert latest["as_of_date"] == date(2025, 7, 15)

    def test_ignore_non_fefta_links(self):
        """Test that non-FEFTA links are ignored."""
        html = """
        <html>
            <body>
                <a href="other.xlsx">Some other list (As of 15 July, 2025)</a>
                <a href="fefta.xlsx">FEFTA List (As of 15 July, 2025)</a>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        links = find_fefta_links(soup, "https://example.com/")

        assert len(links) == 1
        assert "FEFTA" in links[0]["link_text"]

    def test_ignore_non_xlsx_links(self):
        """Test that non-.xlsx links are ignored."""
        html = """
        <html>
            <body>
                <a href="fefta.pdf">FEFTA List (As of 15 July, 2025)</a>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        links = find_fefta_links(soup, "https://example.com/")

        assert len(links) == 0


# =============================================================================
# Test: normalize_circled_numeral
# =============================================================================


class TestNormalizeCircledNumeral:
    """Test the circled numeral to integer conversion."""

    @pytest.mark.parametrize(
        "circled,expected",
        [
            ("①", 1),
            ("②", 2),
            ("③", 3),
            ("④", 4),
            ("⑤", 5),
            ("⑥", 6),
            ("⑦", 7),
            ("⑧", 8),
            ("⑨", 9),
            ("⑩", 10),
        ],
    )
    def test_circled_numerals(self, circled, expected):
        """Test all circled numerals map correctly."""
        result = normalize_circled_numeral(circled, 0, "test")
        assert result == expected

    @pytest.mark.parametrize("plain_digit", ["1", "5", "10", "3.0"])
    def test_plain_digits(self, plain_digit):
        """Test plain digit strings are converted correctly."""
        result = normalize_circled_numeral(plain_digit, 0, "test")
        assert isinstance(result, int)
        assert 1 <= result <= 10

    def test_empty_value_raises_error(self):
        """Test empty value raises FeftaExcelParseError."""
        with pytest.raises(FeftaExcelParseError):
            normalize_circled_numeral("", 0, "category")

    def test_out_of_range_raises_error(self):
        """Test out-of-range value raises FeftaExcelParseError."""
        with pytest.raises(FeftaExcelParseError):
            normalize_circled_numeral("15", 0, "category")

    def test_invalid_value_raises_error(self):
        """Test invalid value raises FeftaExcelParseError."""
        with pytest.raises(FeftaExcelParseError):
            normalize_circled_numeral("abc", 0, "category")


# =============================================================================
# Test: normalize_circled_numeral_optional
# =============================================================================


class TestNormalizeCircledNumeralOptional:
    """Test the optional circled numeral conversion."""

    @pytest.mark.parametrize(
        "circled,expected",
        [
            ("①", 1),
            ("②", 2),
            ("③", 3),
        ],
    )
    def test_circled_numerals(self, circled, expected):
        """Test circled numerals map correctly."""
        result = normalize_circled_numeral_optional(circled, 0, "test")
        assert result == expected

    def test_empty_returns_none(self):
        """Test empty string returns None."""
        assert normalize_circled_numeral_optional("", 0, "core_operator") is None

    def test_dash_returns_none(self):
        """Test dash characters return None."""
        assert normalize_circled_numeral_optional("-", 0, "core_operator") is None
        assert normalize_circled_numeral_optional("－", 0, "core_operator") is None

    def test_none_returns_none(self):
        """Test None value returns None."""
        assert normalize_circled_numeral_optional(None, 0, "core_operator") is None


# =============================================================================
# Test: map_columns
# =============================================================================


class TestMapColumns:
    """Test the column mapping functionality."""

    def test_map_standard_columns(self):
        """Test mapping standard column names."""
        columns = [
            "証券コード (Securities code)",
            "ISINコード (ISIN code)",
            "会社名（和名）",
            "(Issue name / company name)",
            "区分",
            "特定コア事業者",
        ]
        mapping = map_columns(columns)

        assert mapping["証券コード (Securities code)"] == "securities_code"
        assert mapping["ISINコード (ISIN code)"] == "isin_code"
        assert mapping["会社名（和名）"] == "company_name_ja"
        assert mapping["(Issue name / company name)"] == "issue_or_company_name"
        assert mapping["区分"] == "category"
        assert mapping["特定コア事業者"] == "core_operator"

    def test_missing_column_raises_error(self):
        """Test that missing required columns raise error."""
        columns = ["証券コード", "ISINコード"]  # Missing other columns

        with pytest.raises(FeftaExcelParseError) as exc_info:
            map_columns(columns)

        assert "Missing required columns" in str(exc_info.value)

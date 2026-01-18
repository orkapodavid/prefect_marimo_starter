"""
TDnet Announcement Helper Tests
===============================

Unit tests for the tdnet_announcement_helpers module functions.

Documentation: docs/tdnet/TDNET_ANNOUNCEMENT_SCRAPER_GUIDE.md
"""

import pytest
from datetime import date, timedelta

from src.services.tdnet.tdnet_announcement_helpers import (
    format_date_param,
    parse_datetime_text,
    validate_date_range,
    split_date_range,
    calculate_page_count,
    build_request_payload,
    # Japanese helpers
    build_japanese_url,
    parse_japanese_time_text,
)


class TestEnglishHelperFunctions:
    """Tests for English TDnet helper functions."""

    def test_format_date_param(self):
        """Test date formatting to YYYYMMDD."""
        d = date(2026, 1, 15)
        assert format_date_param(d) == "20260115"

        d = date(2025, 12, 1)
        assert format_date_param(d) == "20251201"

    def test_parse_datetime_text(self):
        """Test parsing datetime strings."""
        dt, d = parse_datetime_text("2026/01/15 16:30")
        assert dt.year == 2026
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 16
        assert dt.minute == 30
        assert d == date(2026, 1, 15)

    def test_parse_datetime_text_invalid(self):
        """Test parsing invalid datetime strings."""
        with pytest.raises(ValueError):
            parse_datetime_text("invalid")

    def test_validate_date_range_valid(self):
        """Test valid date range validation."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        is_valid, msg = validate_date_range(yesterday, today)
        assert is_valid is True

    def test_validate_date_range_reversed(self):
        """Test reversed date range validation."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        is_valid, msg = validate_date_range(today, yesterday)
        assert is_valid is False
        assert "before" in msg.lower()

    def test_validate_date_range_exceeds_limit(self):
        """Test date range exceeding 31 days."""
        today = date.today()
        long_ago = today - timedelta(days=60)

        is_valid, msg = validate_date_range(long_ago, today)
        assert is_valid is False
        assert "exceeds" in msg.lower()

    def test_split_date_range_short(self):
        """Test splitting a short date range."""
        start = date(2026, 1, 1)
        end = date(2026, 1, 15)

        chunks = split_date_range(start, end)
        assert len(chunks) == 1
        assert chunks[0] == (start, end)

    def test_split_date_range_long(self):
        """Test splitting a long date range."""
        start = date(2026, 1, 1)
        end = date(2026, 3, 1)  # ~60 days

        chunks = split_date_range(start, end)
        assert len(chunks) >= 2

        # Verify chunks cover the full range
        assert chunks[0][0] == start
        assert chunks[-1][1] == end

    def test_calculate_page_count(self):
        """Test page count calculation."""
        assert calculate_page_count(0) == 1
        assert calculate_page_count(100) == 1
        assert calculate_page_count(200) == 1
        assert calculate_page_count(201) == 2
        assert calculate_page_count(400) == 2
        assert calculate_page_count(401) == 3

    def test_build_request_payload(self):
        """Test building request payload."""
        payload = build_request_payload(date(2026, 1, 14), date(2026, 1, 15), page=2, query="test")

        assert payload["t0"] == "20260114"
        assert payload["t1"] == "20260115"
        assert payload["p"] == "2"
        assert payload["q"] == "test"


class TestJapaneseHelperFunctions:
    """Tests for Japanese TDnet helper functions."""

    def test_build_japanese_url(self):
        """Test building Japanese URL."""
        url = build_japanese_url(1, date(2026, 1, 16))
        assert url == "https://www.release.tdnet.info/inbs/I_list_001_20260116.html"

        url = build_japanese_url(5, date(2026, 1, 16))
        assert url == "https://www.release.tdnet.info/inbs/I_list_005_20260116.html"

    def test_parse_japanese_time_text(self):
        """Test parsing Japanese time text."""
        from datetime import datetime

        dt = parse_japanese_time_text("16:30", date(2026, 1, 16))
        assert dt == datetime(2026, 1, 16, 16, 30)

        dt = parse_japanese_time_text("09:00", date(2026, 1, 16))
        assert dt == datetime(2026, 1, 16, 9, 0)

    def test_parse_japanese_time_text_invalid(self):
        """Test parsing invalid Japanese time text."""
        with pytest.raises(ValueError):
            parse_japanese_time_text("invalid", date(2026, 1, 16))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

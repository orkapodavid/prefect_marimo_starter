"""Unit tests for ASX scraper filters."""

import pytest
from services.asx_scraper.filters import AnnouncementFilters


class TestPIPEFilters:
    """Tests for PIPE announcement filtering."""
    
    def test_is_pipe_announcement_positive(self):
        """Test PIPE keyword detection - positive cases."""
        filters = AnnouncementFilters()
        
        positive_cases = [
            "Capital Raising Announcement",
            "Share Placement Completed",
            "Institutional Placement Notice",
            "Entitlement Offer Update",
            "Rights Issue Announcement",
            "Share Purchase Plan Details",
            "SPP Announcement",
        ]
        
        for headline in positive_cases:
            assert filters.is_pipe_announcement(headline), f"Failed to match: {headline}"
    
    def test_is_pipe_announcement_negative(self):
        """Test PIPE keyword detection - negative cases."""
        filters = AnnouncementFilters()
        
        negative_cases = [
            "Quarterly Activities Report",
            "Financial Results",
            "AGM Notice",
            "Change of Director",
            "Trading Halt",
        ]
        
        for headline in negative_cases:
            assert not filters.is_pipe_announcement(headline), f"False positive: {headline}"
    
    def test_is_pipe_announcement_case_insensitive(self):
        """Test that PIPE matching is case-insensitive."""
        filters = AnnouncementFilters()
        
        assert filters.is_pipe_announcement("CAPITAL RAISING")
        assert filters.is_pipe_announcement("capital raising")
        assert filters.is_pipe_announcement("Capital Raising")
    
    def test_get_matched_pipe_keywords(self):
        """Test getting matched PIPE keywords."""
        filters = AnnouncementFilters()
        
        headline = "Capital raising through institutional placement"
        matched = filters.get_matched_pipe_keywords(headline)
        
        assert "capital raising" in matched
        assert "placement" in matched
        assert "institutional placement" in matched
        assert len(matched) >= 3


class TestAppendix5BFilters:
    """Tests for Appendix 5B filtering."""
    
    def test_is_appendix5b_announcement_positive(self):
        """Test Appendix 5B keyword detection - positive cases."""
        filters = AnnouncementFilters()
        
        positive_cases = [
            "Quarterly Activities Report",
            "Appendix 5B Cash Flow Report",
            "Quarterly Activities and Cash Flow Report",
        ]
        
        for headline in positive_cases:
            assert filters.is_appendix5b_announcement(headline), f"Failed to match: {headline}"
    
    def test_is_appendix5b_announcement_negative(self):
        """Test Appendix 5B keyword detection - negative cases."""
        filters = AnnouncementFilters()
        
        negative_cases = [
            "Capital Raising",
            "Financial Results",
            "AGM Notice",
        ]
        
        for headline in negative_cases:
            assert not filters.is_appendix5b_announcement(headline)
    
    def test_get_matched_appendix5b_keywords(self):
        """Test getting matched Appendix 5B keywords."""
        filters = AnnouncementFilters()
        
        headline = "Quarterly Activities and Cash Flow Report"
        matched = filters.get_matched_appendix5b_keywords(headline)
        
        assert "quarterly activities" in matched
        assert "cash flow report" in matched


class TestDateTimeFilters:
    """Tests for date/time filtering and parsing."""
    
    def test_filter_by_year(self):
        """Test filtering announcements by year."""
        filters = AnnouncementFilters()
        
        announcements = [
            {"datetime": "14/12/2025 8:30 PM", "ticker": "CBA"},
            {"datetime": "15/12/2024 9:00 AM", "ticker": "NAB"},
            {"datetime": "16/12/2025 10:30 AM", "ticker": "BHP"},
            {"datetime": "17/12/2023 2:00 PM", "ticker": "RIO"},
        ]
        
        filtered = filters.filter_by_year(announcements, [2025])
        assert len(filtered) == 2
        assert all(ann["ticker"] in ["CBA", "BHP"] for ann in filtered)
    
    def test_filter_by_multiple_years(self):
        """Test filtering by multiple years."""
        filters = AnnouncementFilters()
        
        announcements = [
            {"datetime": "14/12/2025 8:30 PM", "ticker": "CBA"},
            {"datetime": "15/12/2024 9:00 AM", "ticker": "NAB"},
            {"datetime": "16/12/2023 10:30 AM", "ticker": "BHP"},
        ]
        
        filtered = filters.filter_by_year(announcements, [2024, 2025])
        assert len(filtered) == 2
    
    def test_parse_datetime_to_parts(self):
        """Test parsing datetime string to SQL-compatible parts."""
        filters = AnnouncementFilters()
        
        date_str, time_str = filters.parse_datetime_to_parts("14/12/2025 8:30 PM")
        assert date_str == "2025-12-14"
        assert time_str == "20:30:00"
    
    def test_parse_datetime_am_time(self):
        """Test parsing AM time correctly."""
        filters = AnnouncementFilters()
        
        date_str, time_str = filters.parse_datetime_to_parts("14/12/2025 9:15 AM")
        assert time_str == "09:15:00"
    
    def test_parse_datetime_noon(self):
        """Test parsing 12 PM correctly."""
        filters = AnnouncementFilters()
        
        date_str, time_str = filters.parse_datetime_to_parts("14/12/2025 12:00 PM")
        assert time_str == "12:00:00"
    
    def test_parse_datetime_midnight(self):
        """Test parsing 12 AM correctly."""
        filters = AnnouncementFilters()
        
        date_str, time_str = filters.parse_datetime_to_parts("14/12/2025 12:00 AM")
        assert time_str == "00:00:00"
    
    def test_parse_datetime_invalid(self):
        """Test parsing invalid datetime string."""
        filters = AnnouncementFilters()
        
        date_str, time_str = filters.parse_datetime_to_parts("invalid")
        assert date_str is None
        assert time_str is None


class TestFilenameUtils:
    """Tests for filename utilities."""
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        filters = AnnouncementFilters()
        
        dangerous = 'CBA<>:"/\\|?*Test'
        sanitized = filters.sanitize_filename(dangerous)
        
        assert '<' not in sanitized
        assert '>' not in sanitized
        assert ':' not in sanitized
        assert '"' not in sanitized
        assert '/' not in sanitized
        assert '\\' not in sanitized
        assert '|' not in sanitized
        assert '?' not in sanitized
        assert '*' not in sanitized
    
    def test_sanitize_filename_length_limit(self):
        """Test that filename is truncated to max length."""
        filters = AnnouncementFilters()
        
        long_name = "A" * 300
        sanitized = filters.sanitize_filename(long_name, max_length=200)
        
        assert len(sanitized) <= 200

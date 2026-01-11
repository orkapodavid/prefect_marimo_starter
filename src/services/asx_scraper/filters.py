"""
Filters and business logic for ASX announcements.
"""

import re
import logging
from typing import List
from datetime import datetime

logger = logging.getLogger(__name__)


# PIPE keywords from original scraper
PIPE_KEYWORDS = [
    'placement', 'private placement', 'capital raising', 'capital raise',
    'share placement', 'equity raising', 'equity raise', 'share issue',
    'securities issue', 'institutional placement', 'strategic placement',
    'share subscription', 'convertible note', 'fund raising', 'fundraising',
    'share offer', 'new shares', 'issue of shares', 'issue of securities',
    'proposed issue of securities', 'proposed issue', 'entitlement offer',
    'rights issue', 'share purchase plan', 'spp', 'accelerated non-renounceable',
    'non-renounceable entitlement', 'renounceable entitlement',
    'underwritten placement', 'completion of placement', 'successful placement',
    'institutional offer', 'retail offer',
]

# Appendix 5B keywords
APPENDIX_5B_KEYWORDS = [
    'quarterly activities',
    'cash flow report',
    'appendix 5b',
]


class AnnouncementFilters:
    """Filters for ASX announcements."""
    
    @staticmethod
    def is_pipe_announcement(headline: str) -> bool:
        """
        Check if announcement headline matches PIPE keywords.
        
        Args:
            headline: Announcement headline
            
        Returns:
            True if matches PIPE criteria
        """
        headline_lower = headline.lower()
        return any(keyword in headline_lower for keyword in PIPE_KEYWORDS)
    
    @staticmethod
    def is_appendix5b_announcement(headline: str) -> bool:
        """
        Check if announcement matches Appendix 5B keywords.
        
        Args:
            headline: Announcement headline
            
        Returns:
            True if matches Appendix 5B criteria
        """
        headline_lower = headline.lower()
        return any(keyword in headline_lower for keyword in APPENDIX_5B_KEYWORDS)
    
    @staticmethod
    def get_matched_pipe_keywords(headline: str) -> List[str]:
        """
        Get list of PIPE keywords that match the headline.
        
        Args:
            headline: Announcement headline
            
        Returns:
            List of matched keywords
        """
        headline_lower = headline.lower()
        return [keyword for keyword in PIPE_KEYWORDS if keyword in headline_lower]
    
    @staticmethod
    def get_matched_appendix5b_keywords(headline: str) -> List[str]:
        """
        Get list of Appendix 5B keywords that match the headline.
        
        Args:
            headline: Announcement headline
            
        Returns:
            List of matched keywords
        """
        headline_lower = headline.lower()
        return [keyword for keyword in APPENDIX_5B_KEYWORDS if keyword in headline_lower]
    
    @staticmethod
    def filter_by_year(announcements: List[dict], years: List[int]) -> List[dict]:
        """
        Filter announcements by year.
        
        Args:
            announcements: List of announcement dictionaries
            years: List of years to include
            
        Returns:
            Filtered list of announcements
        """
        filtered = []
        
        for ann in announcements:
            datetime_str = ann.get('datetime', '')
            if not datetime_str:
                continue
            
            # Extract year from datetime string (format: DD/MM/YYYY ...)
            try:
                if '/' in datetime_str:
                    parts = datetime_str.split('/')
                    if len(parts) >= 3:
                        year = int(parts[2][:4])
                        if year in years:
                            filtered.append(ann)
            except (ValueError, IndexError) as e:
                logger.debug(f"Could not extract year from datetime: {datetime_str}, error: {e}")
                continue
        
        logger.info(f"Filtered {len(filtered)} announcements from {len(announcements)} by years {years}")
        return filtered
    
    @staticmethod
    def parse_datetime_to_parts(datetime_str: str) -> tuple:
        """
        Parse datetime string to date and time parts for database storage.
        
        Args:
            datetime_str: DateTime string (e.g., "14/12/2025 8:30 PM")
            
        Returns:
            Tuple of (date_str, time_str) suitable for database
        """
        try:
            # Extract date part (DD/MM/YYYY)
            date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', datetime_str)
            if date_match:
                day, month, year = date_match.groups()
                date_str = f"{year}-{month}-{day}"  # Convert to YYYY-MM-DD
            else:
                date_str = None
            
            # Extract time part
            time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)', datetime_str)
            if time_match:
                hour, minute, period = time_match.groups()
                hour = int(hour)
                # Convert to 24-hour format
                if period.upper() == 'PM' and hour != 12:
                    hour += 12
                elif period.upper() == 'AM' and hour == 12:
                    hour = 0
                time_str = f"{hour:02d}:{minute}:00"
            else:
                time_str = None
            
            return (date_str, time_str)
        except Exception as e:
            logger.error(f"Error parsing datetime '{datetime_str}': {e}")
            return (None, None)
    
    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 200) -> str:
        """
        Sanitize filename for safe file system usage.
        
        Args:
            filename: Original filename
            max_length: Maximum filename length
            
        Returns:
            Sanitized filename
        """
        # Remove invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        return sanitized[:max_length]

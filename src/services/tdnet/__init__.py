"""
TDnet Scrapers Package
======================

This package contains scrapers for TDnet:
- announcement_scraper: For official announcements (English/Japanese)
- search_scraper: For searching third-party allotment deals

Usage:
    from services.tdnet import TdnetAnnouncementScraper, TdnetLanguage
    from services.tdnet import TdnetSearchScraper
"""

from .announcement_models import (
    TdnetLanguage,
    TdnetAnnouncement,
    TdnetScrapeResult,
    AnnouncementNoteType,
)
from .announcement_scraper import (
    TdnetAnnouncementScraper,
    TdnetScraperError,
    TdnetRequestError,
    TdnetParseError,
    scrape_announcements,
)
from .search_models import TdnetSearchEntry, TdnetSearchResult
from .search_scraper import TdnetSearchScraper

__all__ = [
    # Announcement scraper
    "TdnetAnnouncementScraper",
    "TdnetLanguage",
    "TdnetAnnouncement",
    "TdnetScrapeResult",
    "AnnouncementNoteType",
    "TdnetScraperError",
    "TdnetRequestError",
    "TdnetParseError",
    "scrape_announcements",
    # Search scraper
    "TdnetSearchScraper",
    "TdnetSearchEntry",
    "TdnetSearchResult",
]

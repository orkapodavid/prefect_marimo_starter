"""
TDnet Scraper Exceptions
========================

Exception hierarchy for TDnet scraper services.

Documentation: docs/tdnet/TDNET_ANNOUNCEMENT_SCRAPER_GUIDE.md
"""


class TdnetScraperError(Exception):
    """Base exception for TDnet scraper errors."""

    pass


class TdnetRequestError(TdnetScraperError):
    """Raised when a request to TDnet fails."""

    pass


class TdnetParseError(TdnetScraperError):
    """Raised when parsing TDnet HTML fails."""

    pass

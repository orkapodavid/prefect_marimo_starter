"""
FEFTA Crawler Module
====================

This module provides tools for scraping and parsing FEFTA (Foreign Exchange
and Foreign Trade Act) company classification data from the Japanese Ministry
of Finance website.

Usage:
    from services.fefta import FeftaCrawler, FeftaSource, FeftaRecord

    crawler = FeftaCrawler()
    source, records = crawler.run()
"""

from .fefta_models import (
    FeftaSource,
    FeftaRecord,
    FeftaCrawlerError,
    FeftaLinkNotFoundError,
    FeftaDateParseError,
    FeftaExcelParseError,
)
from .fefta_crawler import FeftaCrawler

__all__ = [
    "FeftaCrawler",
    "FeftaSource",
    "FeftaRecord",
    "FeftaCrawlerError",
    "FeftaLinkNotFoundError",
    "FeftaDateParseError",
    "FeftaExcelParseError",
]

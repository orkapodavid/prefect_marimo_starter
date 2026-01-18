"""
FEFTA Crawler Module
====================

This module provides tools for scraping and parsing FEFTA (Foreign Exchange
and Foreign Trade Act) company classification data from the Japanese Ministry
of Finance website.

Usage:
    from src.market_intelligence.fefta import FeftaCrawler, FeftaSource, FeftaRecord

    crawler = FeftaCrawler()
    source, records = crawler.run()
"""

from .models import FeftaSource, FeftaRecord
from .fefta_crawler import (
    FeftaCrawler,
    FeftaCrawlerError,
    FeftaLinkNotFoundError,
    FeftaDateParseError,
    FeftaExcelParseError,
)

__all__ = [
    "FeftaCrawler",
    "FeftaSource",
    "FeftaRecord",
    "FeftaCrawlerError",
    "FeftaLinkNotFoundError",
    "FeftaDateParseError",
    "FeftaExcelParseError",
]

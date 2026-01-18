"""
TDnet Announcement Models
=========================

Pydantic models for TDnet Company Announcements Service data.

Documentation: docs/TDNET_ANNOUNCEMENT_SCRAPER_GUIDE.md

This module provides type-safe data models for representing announcements
scraped from the TDnet Company Announcements Service (English version).
"""

from typing import Optional, List
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import pandas as pd


class TdnetLanguage(str, Enum):
    """Language selection for TDnet scraping."""

    ENGLISH = "english"
    JAPANESE = "japanese"


class AnnouncementNoteType(str, Enum):
    """Types of notes that can appear on announcements."""

    SUMMARY = "Summary"
    DELAYED = "Delayed"
    UPDATED = "Updated"
    NONE = ""


class TdnetAnnouncement(BaseModel):
    """
    Represents a single announcement from TDnet Company Announcements Service.

    This model captures fields from both English and Japanese versions of the
    TDnet announcements table, including the PDF document link.

    Attributes:
        publish_datetime: Full datetime of publication (e.g., 2026-01-15 16:30)
        publish_date: Date portion of publication
        stock_code: 4-5 digit stock code (e.g., "40620")
        company_name: Company name as displayed (e.g., "IBIDEN CO.,LTD.")
        title: Full announcement title
        pdf_url: URL to the PDF document (if available)
        has_xbrl: Whether XBRL data is available for this announcement
        notes: Note type ([Summary], [Delayed], [Updated], or empty)
        language: Language of the announcement (english/japanese)
        sector: Industry sector classification, EN only (e.g., "Electric Appliances")
        listed_exchange: Exchange where company is listed, JP only (e.g., "東", "名")
        xbrl_url: Direct URL to XBRL zip file, JP only

    Example:
        >>> announcement = TdnetAnnouncement(
        ...     publish_datetime=datetime(2026, 1, 15, 16, 30),
        ...     publish_date=date(2026, 1, 15),
        ...     stock_code="40620",
        ...     company_name="IBIDEN CO.,LTD.",
        ...     title="Notice Concerning Tender Offer",
        ...     pdf_url="https://www.release.tdnet.info/inbs/ek/140120260115534185.pdf",
        ...     has_xbrl=False,
        ...     notes="",
        ...     language=TdnetLanguage.ENGLISH,
        ...     sector="Electric Appliances"
        ... )
    """

    publish_datetime: datetime = Field(..., description="Full datetime of publication")
    publish_date: date = Field(..., description="Date of publication")
    stock_code: str = Field(..., description="4-5 digit stock code", min_length=4, max_length=5)
    company_name: str = Field(..., description="Company name")
    title: str = Field(..., description="Announcement title")
    pdf_url: Optional[str] = Field(None, description="URL to PDF document")
    has_xbrl: bool = Field(False, description="Whether XBRL data is available")
    notes: str = Field("", description="Note type: Summary, Delayed, Updated, or empty")
    language: TdnetLanguage = Field(
        TdnetLanguage.ENGLISH, description="Language of the announcement"
    )
    sector: Optional[str] = Field(None, description="Industry sector, EN only")
    listed_exchange: Optional[str] = Field(
        None, description="Listed exchange, JP only (e.g., 東, 名)"
    )
    xbrl_url: Optional[str] = Field(None, description="Direct URL to XBRL zip file, JP only")

    @field_validator("stock_code")
    @classmethod
    def validate_stock_code(cls, v: str) -> str:
        """Validate and clean stock code."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Stock code cannot be empty")
        # Ensure only alphanumeric characters (digits and letters)
        if not cleaned.isalnum():
            raise ValueError("Stock code must contain only alphanumeric characters")
        return cleaned

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, v: str) -> str:
        """Normalize notes field by removing brackets."""
        if v:
            return v.strip().replace("[", "").replace("]", "").replace("〔", "").replace("〕", "")
        return ""

    def to_dict(self) -> dict:
        """Convert to dictionary with string datetime for JSON serialization."""
        return {
            "publish_datetime": self.publish_datetime.isoformat(),
            "publish_date": self.publish_date.isoformat(),
            "stock_code": self.stock_code,
            "company_name": self.company_name,
            "title": self.title,
            "pdf_url": self.pdf_url,
            "has_xbrl": self.has_xbrl,
            "notes": self.notes,
            "language": self.language.value,
            "sector": self.sector,
            "listed_exchange": self.listed_exchange,
            "xbrl_url": self.xbrl_url,
        }


class TdnetScrapeResult(BaseModel):
    """
    Result of a TDnet scraping operation.

    Contains metadata about the scrape operation and the list of announcements.
    Provides convenience methods for converting to pandas DataFrame or list.

    Attributes:
        start_date: Start of the date range queried
        end_date: End of the date range queried
        query: Search query used (empty string if none)
        total_count: Total number of announcements reported by TDnet
        page_count: Number of pages scraped
        announcements: List of TdnetAnnouncement objects
        scraped_at: Timestamp when scraping was performed

    Example:
        >>> result = scraper.scrape(date(2026, 1, 14), date(2026, 1, 15))
        >>> df = result.to_dataframe()
        >>> print(f"Found {len(result.announcements)} announcements")
    """

    start_date: date = Field(..., description="Start of date range")
    end_date: date = Field(..., description="End of date range")
    query: str = Field("", description="Search query used")
    total_count: int = Field(0, description="Total announcements reported by TDnet")
    page_count: int = Field(0, description="Number of pages scraped")
    announcements: List[TdnetAnnouncement] = Field(default_factory=list)
    scraped_at: datetime = Field(default_factory=datetime.now)
    language: TdnetLanguage = Field(TdnetLanguage.ENGLISH, description="Language of the scrape")

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert announcements to a pandas DataFrame.

        Returns:
            pd.DataFrame: DataFrame with all announcement fields as columns.

        Example:
            >>> result = scraper.scrape(start_date, end_date)
            >>> df = result.to_dataframe()
            >>> df.to_csv("announcements.csv", index=False)
        """
        if not self.announcements:
            return pd.DataFrame(
                columns=[
                    "publish_datetime",
                    "publish_date",
                    "stock_code",
                    "company_name",
                    "title",
                    "pdf_url",
                    "has_xbrl",
                    "notes",
                    "language",
                    "sector",
                    "listed_exchange",
                    "xbrl_url",
                ]
            )

        data = [ann.to_dict() for ann in self.announcements]
        df = pd.DataFrame(data)
        df["publish_datetime"] = pd.to_datetime(df["publish_datetime"])
        df["publish_date"] = pd.to_datetime(df["publish_date"]).dt.date
        return df

    def to_list(self) -> List[dict]:
        """
        Convert announcements to a list of dictionaries.

        Returns:
            List[dict]: List of announcement dictionaries.

        Example:
            >>> result = scraper.scrape(start_date, end_date)
            >>> data = result.to_list()
            >>> import json
            >>> json.dump(data, open("announcements.json", "w"))
        """
        return [ann.to_dict() for ann in self.announcements]

    def __len__(self) -> int:
        """Return the number of announcements."""
        return len(self.announcements)

    def __iter__(self):
        """Iterate over announcements."""
        return iter(self.announcements)

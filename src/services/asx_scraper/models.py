"""
Pydantic models for ASX scraper data structures.
"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class Company(BaseModel):
    """Model for an ASX listed company."""
    ticker: str = Field(..., description="ASX ticker code (e.g., CBA)")
    company_name: str = Field(..., description="Full company name")
    
    model_config = ConfigDict(str_strip_whitespace=True)


class Announcement(BaseModel):
    """Model for a single ASX announcement."""
    ticker: str
    datetime: str = Field(..., description="Announcement date/time as string")
    price_sensitive: bool = False
    headline: str
    pdf_url: str
    number_of_pages: Optional[int] = None
    file_size: Optional[str] = None
    
    model_config = ConfigDict(str_strip_whitespace=True)


class Section8Data(BaseModel):
    """Model for extracted Section 8 data from Appendix 5B reports."""
    section_8_found: bool = False
    item_8_6_total_available_funding: Optional[float] = None
    item_8_7_estimated_quarters: Optional[Union[float, str]] = None
    raw_section_8_text: Optional[str] = None


class ScrapeResult(BaseModel):
    """Model for the result of a single scrape operation (Appendix 5B)."""
    date: str
    stock_code: str
    headline: str
    pdf_link: str
    matched_keywords: List[str] = Field(default_factory=list)
    pdf_downloaded: bool = False
    pdf_filename: Optional[str] = None
    extraction_success: bool = False
    section_8_data: Section8Data = Field(default_factory=Section8Data)
    warning: Optional[str] = None


class ScrapeSummary(BaseModel):
    """Model for the overall scrape summary (Appendix 5B)."""
    scrape_datetime: str
    total_announcements_found: int
    successful_extractions: int
    warnings_count: int
    results: List[ScrapeResult]
    summary_file: Optional[str] = None

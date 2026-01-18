from typing import Optional, List, Dict
from datetime import datetime
from datetime import date as DateType
from pydantic import BaseModel, Field

class TdnetSearchEntry(BaseModel):
    """
    Represents a single entry from TDnet Search results.
    """
    date: DateType = Field(..., description="Date of the announcement")
    datetime_str: str = Field(..., description="Original datetime string from table")
    stock_code: str = Field(..., description="Stock code")
    company_name: str = Field(..., description="Company name")
    title: str = Field(..., description="Announcement title")
    pdf_link: Optional[str] = Field(None, description="URL to PDF")
    description: Optional[str] = Field(None, description="Description/Summary")
    doc_id: Optional[str] = Field(None, description="Document ID")
    tier: Optional[str] = Field(None, description="Search tier matched")
    
    # Deal details (optional, from PDF extraction)
    investor: Optional[str] = Field(None, description="Allottee/Investor")
    deal_size: Optional[str] = Field(None, description="Deal size amount")
    deal_size_currency: Optional[str] = Field(None, description="Currency of deal size")
    share_price: Optional[str] = Field(None, description="Issue price")
    share_count: Optional[str] = Field(None, description="Number of shares/warrants")
    deal_date: Optional[str] = Field(None, description="Deal execution date")
    deal_structure: Optional[str] = Field(None, description="Type of deal (Stock, Warrant, etc.)")

class TdnetSearchResult(BaseModel):
    """
    Result of a scraping session.
    """
    start_date: Optional[DateType]
    end_date: Optional[DateType]
    entries: List[TdnetSearchEntry]
    total_count: int
    scraped_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict = Field(default_factory=dict)

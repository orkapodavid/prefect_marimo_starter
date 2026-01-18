"""
FEFTA Data Models
=================

Pydantic v2 models for FEFTA (Foreign Exchange and Foreign Trade Act)
company classification data.
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class FeftaSource(BaseModel):
    """
    Metadata about the FEFTA Excel source file.

    Attributes:
        as_of_raw: Raw "As of" text from the link (e.g., "As of 15 July, 2025")
        as_of_date: Parsed date from as_of_raw in ISO format
        download_date: Date when the file was downloaded
        file_url: Absolute URL to the Excel file
        saved_path: Local path where the Excel file was saved (None until downloaded)
    """

    as_of_raw: str = Field(..., description="Raw 'As of' text from link")
    as_of_date: date = Field(..., description="Parsed date from as_of_raw")
    download_date: date = Field(..., description="Date when file was downloaded")
    file_url: str = Field(..., description="Absolute URL to the Excel file")
    saved_path: Optional[str] = Field(None, description="Local path where Excel was saved")


class FeftaRecord(BaseModel):
    """
    A single record from the FEFTA listed companies classification sheet.

    Maps Japanese column names to English field names while preserving
    Japanese values where applicable.

    Attributes:
        securities_code: 証券コード (Securities code) - preserved as string
        isin_code: ISINコード (ISIN code) - preserved as string
        company_name_ja: 会社名（和名）- Japanese company name
        issue_or_company_name: (Issue name / company name) - English/alternative name
        category: 区分 - Category (1-10, mapped from circled numerals)
        core_operator: 特定コア事業者 - Core operator designation (1-10)
    """

    securities_code: str = Field(..., description="証券コード (Securities code)", min_length=1)
    isin_code: str = Field(..., description="ISINコード (ISIN code)", min_length=1)
    company_name_ja: str = Field(..., description="会社名（和名）- Japanese company name")
    issue_or_company_name: str = Field(..., description="(Issue name / company name)")
    category: int = Field(..., description="区分 - Category (1-10)", ge=1, le=10)
    core_operator: Optional[int] = Field(
        None,
        description="特定コア事業者 - Core operator (1-10, None if not designated)",
    )

    @field_validator("securities_code", "isin_code", mode="before")
    @classmethod
    def coerce_to_string(cls, v):
        """Ensure codes are strings to preserve leading zeros."""
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("company_name_ja", "issue_or_company_name", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        """Strip whitespace from text fields."""
        if v is None:
            return ""
        return str(v).strip()

"""Pydantic models for financial monitor configuration and workflow data."""

from datetime import date, datetime
from pathlib import Path
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class FinancialMonitorRuntime(BaseModel):
    """Runtime settings that apply to a monitor run."""

    workspace_dir: Path | None = None
    schedule_cron: str | None = None


class FinancialMonitorDefaults(BaseModel):
    """Defaults merged onto every configured target."""

    timezone: str = "Asia/Tokyo"
    runway_threshold_months: int = 12


class FinancialMonitorCompany(BaseModel):
    """Company registry metadata shared by one or more targets."""

    name: str
    ticker: str = ""
    exchange: str = ""
    edinet_code: str = ""


class FinancialMonitorTarget(BaseModel):
    """A single configured financial-monitor target."""

    id: str
    company_id: str
    company_name: str = ""
    ticker: str = ""
    exchange: str = ""
    edinet_code: str = ""
    tdnet_language: Literal["japanese", "english"]
    disclosure_keywords: list[str] = Field(default_factory=list)
    include_edinet: bool = True
    enabled: bool = True
    timezone: str = "Asia/Tokyo"
    runway_threshold_months: int = 12

    @field_validator("disclosure_keywords")
    @classmethod
    def validate_disclosure_keywords(cls, value: list[str]) -> list[str]:
        cleaned = [keyword.strip() for keyword in value if keyword and keyword.strip()]
        if not cleaned:
            raise ValueError("disclosure_keywords must contain at least one keyword")
        return cleaned


class FinancialMonitorConfig(BaseModel):
    """Top-level financial monitor configuration."""

    companies: dict[str, FinancialMonitorCompany] = Field(default_factory=dict)
    runtime: FinancialMonitorRuntime = Field(default_factory=FinancialMonitorRuntime)
    defaults: FinancialMonitorDefaults = Field(default_factory=FinancialMonitorDefaults)
    targets: list[FinancialMonitorTarget] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_target_ids(self) -> "FinancialMonitorConfig":
        seen_target_ids: set[str] = set()
        for target in self.targets:
            if target.id in seen_target_ids:
                raise ValueError(f"Duplicate target id: {target.id}")
            seen_target_ids.add(target.id)
            if not target.company_name.strip():
                raise ValueError(f"Target {target.id} must resolve to a non-empty company_name")
        return self


class FinancialMonitorTdnetCandidate(BaseModel):
    """Normalized TDnet announcement candidate for downstream processing."""

    target_id: str
    company_id: str
    company_name: str
    company_code: str
    ticker: str = ""
    exchange: str = ""
    edinet_code: str = ""
    title: str
    disclosure_date: date
    source_url: str
    pdf_url: str | None = None
    xbrl_url: str | None = None
    has_xbrl: bool = False
    source_system: Literal["tdnet"] = "tdnet"


class FinancialMonitorEdinetDocument(BaseModel):
    """Normalized EDINET document metadata."""

    document_id: str
    edinet_code: str
    filer_name: str
    securities_code: str | None = None
    description: str
    form_code: str | None = None
    filed_at: datetime
    has_xbrl: bool = False
    has_pdf: bool = False
    has_csv: bool = False
    xbrl_download_url: str | None = None
    pdf_download_url: str | None = None
    csv_download_url: str | None = None
    raw: dict = Field(default_factory=dict)
    source_system: Literal["edinet"] = "edinet"

    @field_validator("document_id", "edinet_code", "filer_name", "description", mode="before")
    @classmethod
    def normalize_required_text_fields(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()


class FinancialMonitorFilingRecord(BaseModel):
    """Normalized filing metadata for persistence."""

    company_id: str
    company_code: str
    company_name: str
    exchange: str = ""
    edinet_code: str = ""
    source_system: str
    document_id: str
    filing_date: date
    title: str
    source_url: str
    local_raw_path: str | None = None


class FinancialMonitorCashMetricRecord(BaseModel):
    """Extracted cash metrics for a filing."""

    period_end: date | None = None
    currency: str = "JPY"
    cash: float | None = None
    operating_cash_flow: float | None = None
    investing_cash_flow: float | None = None
    financing_cash_flow: float | None = None
    monthly_burn: float | None = None
    runway_months: float | None = None
    tag_names: dict[str, str] = Field(default_factory=dict)


class FinancialMonitorIntentSignalRecord(BaseModel):
    """A deterministic intent signal extracted from management text."""

    signal_type: str
    matched_phrase: str
    excerpt: str
    source_section: str
    match_rule: str

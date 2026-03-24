"""Pydantic models for the IR monitor feature."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class MonitorDefaults(BaseModel):
    """Defaults applied to each configured monitor target."""

    timezone: str = "Asia/Tokyo"
    report_timezone: str = "Asia/Tokyo"


class MonitorRuntime(BaseModel):
    """Runtime settings that apply to a monitor run, not individual targets."""

    notify_on_no_change: bool = False
    workspace_dir: Path | None = None
    schedule_cron: str | None = None


class CompanyEntry(BaseModel):
    """A company registry entry shared by one or more monitor targets."""

    name: str
    ticker: str = ""
    exchange: str = ""


class MonitorTarget(BaseModel):
    """A single monitored IR target."""

    id: str
    company_id: str
    company_name: str = ""
    ticker: str = ""
    exchange: str = ""
    page_label: str
    page_url: str
    user_visible_url: str
    target_kind: Literal["html_list", "json_feed", "pdf_document"]
    selector_type: str
    selector: str = ""
    normalizer: str
    enabled: bool = True
    country: str = "JP"
    language: str = "ja"
    use_browser: bool = False
    diff_mode: Literal["additions_only", "unified"] | None = None
    timezone: str = "Asia/Tokyo"
    report_timezone: str = "Asia/Tokyo"
    notes: str = ""

    @model_validator(mode="after")
    def apply_target_defaults(self) -> "MonitorTarget":
        if self.diff_mode is None:
            if self.target_kind == "pdf_document":
                self.diff_mode = "unified"
            else:
                self.diff_mode = "additions_only"
        return self


class MonitorConfig(BaseModel):
    """Top-level IR monitor configuration."""

    companies: dict[str, CompanyEntry] = Field(default_factory=dict)
    runtime: MonitorRuntime = Field(default_factory=MonitorRuntime)
    defaults: MonitorDefaults = Field(default_factory=MonitorDefaults)
    targets: list[MonitorTarget] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_target_ids(self) -> "MonitorConfig":
        seen_target_ids: set[str] = set()
        for target in self.targets:
            if target.id in seen_target_ids:
                raise ValueError(f"Duplicate target id: {target.id}")
            seen_target_ids.add(target.id)
            if not target.company_name.strip():
                raise ValueError(
                    f"Target {target.id} must resolve to a non-empty company_name"
                )
        return self


class NormalizedItemRecord(BaseModel):
    """A normalized disclosure item."""

    item_key: str
    date: str | None = None
    title: str
    url: str
    item_type: str = "html"
    language: str = "ja"


class MonitorChangeEvent(BaseModel):
    """A parsed change record from a webchanges run."""

    company_id: str
    company_name: str
    ticker: str = ""
    exchange: str = ""
    target_id: str
    page_label: str
    status: str
    diff_mode: str = "additions_only"
    added_lines: list[str] = Field(default_factory=list)
    removed_lines: list[str] = Field(default_factory=list)
    before_lines: list[str] = Field(default_factory=list)
    after_lines: list[str] = Field(default_factory=list)
    error_message: str | None = None


class NotificationPayload(BaseModel):
    """Notification-ready summary payload."""

    environment: str
    run_label: str
    changed_companies: int
    changed_targets: int
    events: list[MonitorChangeEvent] = Field(default_factory=list)


class WorkspacePaths(BaseModel):
    """Resolved workspace paths for an IR monitor run."""

    root_dir: Path
    generated_dir: Path
    jobs_path: Path
    config_path: Path
    state_dir: Path
    artifacts_dir: Path
    logs_dir: Path
    changed_jobs_path: Path
    baseline_metadata_path: Path


class CommandResult(BaseModel):
    """Captured subprocess result for a webchanges run."""

    exit_code: int
    stdout: str
    stderr: str
    changed_jobs_path: Path
    baseline_target_ids: list[str] = Field(default_factory=list)


class ParsedMonitorReport(BaseModel):
    """Parsed change summary from a webchanges run."""

    events: list[MonitorChangeEvent] = Field(default_factory=list)
    changed_count: int = 0
    unchanged_target_ids: list[str] = Field(default_factory=list)
    failed_target_ids: list[str] = Field(default_factory=list)
    baseline_target_ids: list[str] = Field(default_factory=list)
    raw_report: str = ""


class ArtifactPaths(BaseModel):
    """Paths to generated artifact files for a run."""

    run_dir: Path
    raw_report_path: Path
    changes_json_path: Path
    changes_markdown_path: Path


class NotificationResult(BaseModel):
    """Outcome of a notification attempt."""

    sent: bool
    channel: str
    message: str

"""Pydantic models for X monitor configuration and core data objects."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class XMonitorRuntime(BaseModel):
    """Runtime settings that apply to the monitor as a whole."""

    timezone: str = "Asia/Singapore"
    poll_batch_limit: int = 25
    poll_window_minutes: int = 15
    immediate_alerts_enabled: bool = True
    daily_digest_enabled: bool = True
    subject_prefix: str = "[X Monitor]"
    workspace_dir: Path | None = None
    poll_cron: str | None = None
    digest_cron: str | None = None
    health_cron: str | None = None


class XMonitorDefaults(BaseModel):
    """Defaults merged onto every configured target."""

    include_replies: bool = False
    include_retweets: bool = False
    media_only: bool = False


class XMonitorTarget(BaseModel):
    """A single monitored X account."""

    id: str
    username: str
    user_id: str | None = None
    include_replies: bool = False
    include_retweets: bool = False
    media_only: bool = False
    keywords_any: list[str] = Field(default_factory=list)
    keywords_all: list[str] = Field(default_factory=list)
    regex_any: list[str] = Field(default_factory=list)
    alert_recipients: list[str] = Field(default_factory=list)
    digest_recipients: list[str] = Field(default_factory=list)
    active: bool = True


class XMonitorConfig(BaseModel):
    """Top-level X monitor configuration."""

    runtime: XMonitorRuntime = Field(default_factory=XMonitorRuntime)
    defaults: XMonitorDefaults = Field(default_factory=XMonitorDefaults)
    targets: list[XMonitorTarget] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_target_ids(self) -> "XMonitorConfig":
        seen_target_ids: set[str] = set()
        for target in self.targets:
            if target.id in seen_target_ids:
                raise ValueError(f"Duplicate target id: {target.id}")
            seen_target_ids.add(target.id)
        return self


class XMonitorMatchResult(BaseModel):
    """Structured outcome of match evaluation."""

    matched: bool
    matched_rules: list[str] = Field(default_factory=list)
    match_reason: str | None = None


class XMonitorNotificationPayload(BaseModel):
    """Notification payload prepared for email delivery."""

    kind: str
    provider: str
    recipient: str
    subject: str
    text_body: str
    html_body: str | None = None
    idempotency_key: str
    post_id: str | None = None
    target_id: str | None = None


class XMonitorNormalizedPost(BaseModel):
    """Normalized representation of a collected X post."""

    post_id: str
    target_id: str
    author_username: str
    author_user_id: str | None = None
    created_at: datetime
    text_raw: str
    text_normalized: str
    url: str
    is_reply: bool = False
    is_retweet: bool = False
    has_media: bool = False
    lang: str | None = None
    raw_json: dict = Field(default_factory=dict)


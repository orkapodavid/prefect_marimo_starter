"""Parse structured and text webchanges reports into monitor events."""

import json
import re
from typing import Any

from services.ir_monitor.ir_monitor_models import MonitorChangeEvent, ParsedMonitorReport


def _infer_company_id(target_id: str) -> str:
    if "_ir_" in target_id:
        return target_id.split("_ir_", maxsplit=1)[0]
    if "_" in target_id:
        return target_id.rsplit("_", maxsplit=1)[0]
    return target_id


def _infer_company_name(company_id: str) -> str:
    return company_id.replace("_", " ").title()


def _event_metadata(
    target_id: str,
    target_metadata_by_id: dict[str, dict[str, str]],
    structured_metadata_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    metadata = {}
    metadata.update(target_metadata_by_id.get(target_id, {}))
    metadata.update(structured_metadata_by_id.get(target_id, {}))
    return metadata


def _baseline_events(
    baseline_target_ids: list[str],
    target_metadata_by_id: dict[str, dict[str, str]],
    structured_metadata_by_id: dict[str, dict[str, Any]],
) -> list[MonitorChangeEvent]:
    events: list[MonitorChangeEvent] = []
    for target_id in baseline_target_ids:
        metadata = _event_metadata(target_id, target_metadata_by_id, structured_metadata_by_id)
        company_id = metadata.get("company_id") or _infer_company_id(target_id)
        events.append(
            MonitorChangeEvent(
                company_id=company_id,
                company_name=metadata.get("company_name") or _infer_company_name(company_id),
                ticker=metadata.get("ticker", ""),
                exchange=metadata.get("exchange", ""),
                target_id=target_id,
                page_label=metadata.get("page_label") or target_id,
                status="baseline_initialized",
                diff_mode=metadata.get("diff_mode", "additions_only"),
            )
        )
    return events


def _parse_structured_payload(changed_jobs_payload: str) -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(changed_jobs_payload)
    except json.JSONDecodeError:
        return {}

    if not isinstance(payload, list):
        return {}

    structured_metadata_by_id: dict[str, dict[str, Any]] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        target_id = item.get("target_id") or item.get("name")
        if not target_id:
            continue
        structured_metadata_by_id[target_id] = {
            key: value
            for key, value in item.items()
            if key
            in {
                "target_id",
                "company_id",
                "company_name",
                "ticker",
                "exchange",
                "page_label",
                "status",
                "diff_mode",
                "before_lines",
                "after_lines",
                "error_message",
            }
            and value is not None
        }

    return structured_metadata_by_id


def _parse_stdout(raw_report: str) -> tuple[list[MonitorChangeEvent], set[str], set[str]]:
    events: list[MonitorChangeEvent] = []
    explicit_unchanged: set[str] = set()
    failed_target_ids: set[str] = set()
    current_status: str | None = None
    current_target_id: str | None = None
    added_lines: list[str] = []
    removed_lines: list[str] = []
    error_lines: list[str] = []

    def finalize_block() -> None:
        if current_status is None or current_target_id is None:
            return

        if current_status == "UNCHANGED":
            explicit_unchanged.add(current_target_id)
            return
        if current_status == "CHANGED" and not added_lines and not removed_lines:
            return

        company_id = _infer_company_id(current_target_id)
        if current_status == "ERROR":
            failed_target_ids.add(current_target_id)
            events.append(
                MonitorChangeEvent(
                    company_id=company_id,
                    company_name=_infer_company_name(company_id),
                    target_id=current_target_id,
                    page_label=current_target_id,
                    status="failed",
                    error_message=" ".join(error_lines).strip(),
                )
            )
            return

        events.append(
            MonitorChangeEvent(
                company_id=company_id,
                company_name=_infer_company_name(company_id),
                target_id=current_target_id,
                page_label=current_target_id,
                status="changed",
                added_lines=added_lines.copy(),
                removed_lines=removed_lines.copy(),
            )
        )

    header_pattern = re.compile(r"^(CHANGED|UNCHANGED|ERROR):\s+(.+?)(?:\s+\(.+\))?$")
    for line in raw_report.splitlines():
        header_match = header_pattern.match(line.strip())
        if header_match:
            finalize_block()
            current_status = header_match.group(1)
            current_target_id = header_match.group(2)
            added_lines = []
            removed_lines = []
            error_lines = []
            continue

        if current_status == "CHANGED":
            stripped_line = line.strip()
            if not stripped_line:
                continue
            if re.fullmatch(r"[-=]{5,}", stripped_line) or stripped_line == "--":
                continue
            if stripped_line.startswith("/**Comparison type:"):
                continue
            if stripped_line.startswith("+++ @") or stripped_line.startswith("--- @"):
                continue
            if line.startswith("+"):
                added_lines.append(line[1:].strip())
            elif line.startswith("-"):
                removed_lines.append(line[1:].strip())
        elif current_status == "ERROR" and line.strip():
            error_lines.append(line.strip())

    finalize_block()
    return events, explicit_unchanged, failed_target_ids


def parse_monitor_report(
    raw_report: str,
    changed_jobs_payload: str | None,
    enabled_target_ids: list[str],
    baseline_target_ids: list[str],
    target_metadata_by_id: dict[str, dict[str, str]] | None = None,
) -> ParsedMonitorReport:
    """Parse structured or text webchanges output into monitor events."""
    resolved_target_metadata = target_metadata_by_id or {}
    structured_metadata_by_id = (
        _parse_structured_payload(changed_jobs_payload) if changed_jobs_payload else {}
    )
    baseline_events = _baseline_events(
        baseline_target_ids=baseline_target_ids,
        target_metadata_by_id=resolved_target_metadata,
        structured_metadata_by_id=structured_metadata_by_id,
    )
    failed_target_ids: set[str] = set()
    parsed_events, explicit_unchanged, failed_target_ids = _parse_stdout(raw_report)

    if not parsed_events and structured_metadata_by_id:
        parsed_events = []
        for target_id, metadata in structured_metadata_by_id.items():
            company_id = metadata.get("company_id") or _infer_company_id(target_id)
            parsed_events.append(
                MonitorChangeEvent(
                    company_id=company_id,
                    company_name=metadata.get("company_name") or _infer_company_name(company_id),
                    ticker=metadata.get("ticker", ""),
                    exchange=metadata.get("exchange", ""),
                    target_id=target_id,
                    page_label=metadata.get("page_label") or target_id,
                    status=metadata.get("status", "changed"),
                    diff_mode=metadata.get("diff_mode", "additions_only"),
                    before_lines=metadata.get("before_lines", []),
                    after_lines=metadata.get("after_lines", []),
                    error_message=metadata.get("error_message"),
                )
            )

    for event in parsed_events:
        metadata = _event_metadata(
            event.target_id,
            resolved_target_metadata,
            structured_metadata_by_id,
        )
        event.company_id = metadata.get("company_id") or event.company_id
        event.company_name = metadata.get("company_name") or event.company_name
        event.ticker = metadata.get("ticker") or event.ticker
        event.exchange = metadata.get("exchange") or event.exchange
        event.page_label = metadata.get("page_label") or event.page_label
        event.diff_mode = metadata.get("diff_mode") or event.diff_mode

    changed_target_ids = {event.target_id for event in parsed_events if event.status == "changed"}
    failed_target_ids.update(
        event.target_id for event in parsed_events if event.status == "failed"
    )
    inferred_unchanged = set(enabled_target_ids) - changed_target_ids - failed_target_ids - set(
        baseline_target_ids
    )
    unchanged_target_ids = sorted(explicit_unchanged | inferred_unchanged)

    all_events = parsed_events + baseline_events
    return ParsedMonitorReport(
        events=all_events,
        changed_count=sum(event.status == "changed" for event in parsed_events),
        unchanged_target_ids=unchanged_target_ids,
        failed_target_ids=sorted(failed_target_ids),
        baseline_target_ids=baseline_target_ids,
        raw_report=raw_report,
    )

"""Parse structured and text webchanges reports into monitor events."""

import json
import re

from services.ir_monitor.ir_monitor_models import MonitorChangeEvent, ParsedMonitorReport


def _infer_company_id(target_id: str) -> str:
    if "_ir_" in target_id:
        return target_id.split("_ir_", maxsplit=1)[0]
    if "_" in target_id:
        return target_id.rsplit("_", maxsplit=1)[0]
    return target_id


def _infer_company_name(company_id: str) -> str:
    return company_id.replace("_", " ").title()


def _baseline_events(baseline_target_ids: list[str]) -> list[MonitorChangeEvent]:
    events: list[MonitorChangeEvent] = []
    for target_id in baseline_target_ids:
        company_id = _infer_company_id(target_id)
        events.append(
            MonitorChangeEvent(
                company_id=company_id,
                company_name=_infer_company_name(company_id),
                target_id=target_id,
                page_label=target_id,
                status="baseline_initialized",
            )
        )
    return events


def _parse_structured_payload(changed_jobs_payload: str) -> list[MonitorChangeEvent]:
    payload = json.loads(changed_jobs_payload)
    events: list[MonitorChangeEvent] = []

    for item in payload:
        target_id = item.get("target_id") or item.get("name") or ""
        company_id = item.get("company_id") or _infer_company_id(target_id)
        events.append(
            MonitorChangeEvent(
                company_id=company_id,
                company_name=item.get("company_name") or _infer_company_name(company_id),
                target_id=target_id,
                page_label=item.get("page_label") or target_id,
                status=item.get("status", "changed"),
                diff_mode=item.get("diff_mode", "additions_only"),
                added_lines=item.get("added_lines", []),
                removed_lines=item.get("removed_lines", []),
                before_lines=item.get("before_lines", []),
                after_lines=item.get("after_lines", []),
                error_message=item.get("error_message"),
            )
        )

    return events


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

        company_id = _infer_company_id(current_target_id)
        if current_status == "UNCHANGED":
            explicit_unchanged.add(current_target_id)
            return
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

    header_pattern = re.compile(r"^(CHANGED|UNCHANGED|ERROR):\s+(.+)$")
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
) -> ParsedMonitorReport:
    """Parse structured or text webchanges output into monitor events."""
    baseline_events = _baseline_events(baseline_target_ids)
    failed_target_ids: set[str] = set()

    if changed_jobs_payload:
        parsed_events = _parse_structured_payload(changed_jobs_payload)
        explicit_unchanged: set[str] = set()
    else:
        parsed_events, explicit_unchanged, failed_target_ids = _parse_stdout(raw_report)

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

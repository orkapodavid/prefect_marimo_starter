"""Artifact writers for IR monitor runs."""

import json
from pathlib import Path

from services.ir_monitor.ir_monitor_models import ArtifactPaths


def _company_display_name(event: dict) -> str:
    ticker = event.get("ticker", "")
    company_name = event["company_name"]
    if ticker:
        return f"{company_name} ({ticker})"
    return company_name


def _group_events_by_company(parsed_events: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for event in parsed_events:
        grouped.setdefault(_company_display_name(event), []).append(event)
    return grouped


def _build_markdown(parsed_events: list[dict], run_label: str) -> str:
    lines = [f"# IR Monitor Summary {run_label}", ""]
    grouped_events = _group_events_by_company(parsed_events)

    for company_name in sorted(grouped_events):
        lines.append(f"## {company_name}")
        lines.append("")
        for event in grouped_events[company_name]:
            lines.append(
                f"- {event['page_label']} [{event['target_id']}] "
                f"status={event['status']} diff_mode={event['diff_mode']}"
            )
            for added_line in event.get("added_lines", []):
                lines.append(f"  - {added_line}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def write_run_artifacts(
    workspace_dir: Path,
    raw_report: str,
    parsed_events: list[dict],
    run_label: str,
) -> ArtifactPaths:
    """Write timestamped raw and summarized artifacts for a run."""
    run_dir = workspace_dir / run_label
    run_dir.mkdir(parents=True, exist_ok=True)

    artifact_paths = ArtifactPaths(
        run_dir=run_dir,
        raw_report_path=run_dir / "raw_report.txt",
        changes_json_path=run_dir / "changes.json",
        changes_markdown_path=run_dir / "changes.md",
    )

    artifact_paths.raw_report_path.write_text(raw_report, encoding="utf-8")
    artifact_paths.changes_json_path.write_text(
        json.dumps(parsed_events, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    artifact_paths.changes_markdown_path.write_text(
        _build_markdown(parsed_events, run_label),
        encoding="utf-8",
    )

    return artifact_paths

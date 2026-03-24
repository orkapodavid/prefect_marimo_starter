"""Notification helpers for IR monitor content changes."""

import json
import logging

import requests

from services.ir_monitor.ir_monitor_models import NotificationResult

LOGGER = logging.getLogger(__name__)


def _changed_events(parsed_events: list[dict]) -> list[dict]:
    return [event for event in parsed_events if event.get("status") == "changed"]


def _build_message(
    parsed_events: list[dict],
    environment: str,
    run_label: str,
    artifact_path: str,
) -> str:
    changed_events = _changed_events(parsed_events)
    changed_companies = sorted({event["company_name"] for event in changed_events})
    lines = [
        f"IR monitor changes detected in {environment}",
        f"Run: {run_label}",
        f"Changed companies: {len(changed_companies)}",
        f"Changed targets: {len(changed_events)}",
        f"Artifacts: {artifact_path}",
    ]
    for company_name in changed_companies:
        lines.append(f"- {company_name}")
        for event in changed_events:
            if event["company_name"] == company_name:
                lines.append(f"  {event['page_label']} ({event['target_id']})")
    return "\n".join(lines)


def notify_if_needed(
    parsed_events: list[dict],
    environment: str,
    run_label: str,
    artifact_path: str,
    webhook_url: str,
    notify_on_no_change: bool,
) -> NotificationResult:
    """Send a concise webhook notification or fall back to logs."""
    changed_events = _changed_events(parsed_events)
    if not changed_events and not notify_on_no_change:
        return NotificationResult(sent=False, channel="none", message="")

    message = _build_message(parsed_events, environment, run_label, artifact_path)
    if changed_events and webhook_url:
        try:
            response = requests.post(
                webhook_url,
                json={"text": message},
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException:
            LOGGER.exception("IR monitor webhook notification failed; falling back to log output.")
        else:
            return NotificationResult(sent=True, channel="webhook", message=message)

    LOGGER.info("%s", json.dumps({"message": message}, ensure_ascii=False))
    return NotificationResult(sent=False, channel="log", message=message)

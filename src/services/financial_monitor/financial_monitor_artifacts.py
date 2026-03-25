"""Artifact writers for financial monitor runs."""

import json
from pathlib import Path

def _build_markdown(summary: dict, run_label: str) -> str:
    lines = [f"# Financial Monitor Summary {run_label}", ""]
    lines.append(f"- Environment: {summary['environment']}")
    lines.append(f"- Filing date: {summary['filing_date']}")
    lines.append(f"- TDnet candidates: {summary['tdnet_candidate_count']}")
    lines.append(f"- EDINET candidates: {summary['edinet_candidate_count']}")
    lines.append(f"- Extracted metric records: {summary['extracted_metric_count']}")
    lines.append(f"- Persisted filings: {summary['persisted']['filings_upserted']}")
    lines.append("")
    return "\n".join(lines)


def write_financial_monitor_run_artifacts(
    reports_dir: Path,
    run_label: str,
    summary: dict,
) -> dict[str, Path]:
    """Write JSON and Markdown artifacts for a financial monitor run."""
    run_dir = reports_dir / run_label
    run_dir.mkdir(parents=True, exist_ok=True)

    artifact_paths = {
        "run_dir": run_dir,
        "summary_json_path": run_dir / "summary.json",
        "summary_markdown_path": run_dir / "summary.md",
    }
    artifact_paths["summary_json_path"].write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    artifact_paths["summary_markdown_path"].write_text(
        _build_markdown(summary, run_label),
        encoding="utf-8",
    )
    return artifact_paths

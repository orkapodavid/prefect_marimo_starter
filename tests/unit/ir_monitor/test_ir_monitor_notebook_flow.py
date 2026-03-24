from pathlib import Path
from unittest.mock import Mock
import importlib

import pytest

from src.services.ir_monitor.ir_monitor_models import (
    ArtifactPaths,
    CommandResult,
    MonitorConfig,
    MonitorDefaults,
    MonitorRuntime,
    MonitorTarget,
    ParsedMonitorReport,
    WorkspacePaths,
)


def test_run_ir_webchanges_monitor_raises_when_webchanges_exits_non_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    notebook = importlib.import_module("notebooks.ir.ir_webchanges_monitor")

    config = MonitorConfig(
        runtime=MonitorRuntime(),
        defaults=MonitorDefaults(report_timezone="Asia/Tokyo"),
        targets=[
            MonitorTarget(
                id="mitsubishi_corp_ir_ja",
                company_id="mitsubishi_corp",
                company_name="Mitsubishi Corporation",
                page_label="Japanese IR page",
                page_url="https://example.com/ir",
                user_visible_url="https://example.com/ir",
                target_kind="html_list",
                normalizer="generic_jp_ir_news",
                enabled=True,
            )
        ],
    )
    workspace = WorkspacePaths(
        root_dir=tmp_path,
        generated_dir=tmp_path / "generated",
        jobs_path=tmp_path / "generated/jobs.yaml",
        config_path=tmp_path / "generated/config.yaml",
        state_dir=tmp_path / "state",
        artifacts_dir=tmp_path / "artifacts",
        logs_dir=tmp_path / "logs",
        changed_jobs_path=tmp_path / "artifacts/changed_jobs.json",
        baseline_metadata_path=tmp_path / "state/baselines.json",
    )
    command_result = CommandResult(
        exit_code=2,
        stdout="",
        stderr="webchanges failed",
        changed_jobs_path=workspace.changed_jobs_path,
        baseline_target_ids=[],
    )
    parsed_report = ParsedMonitorReport(
        failed_target_ids=["mitsubishi_corp_ir_ja"],
        raw_report="webchanges failed",
    )
    artifact_paths = ArtifactPaths(
        run_dir=tmp_path / "artifacts/run",
        raw_report_path=tmp_path / "artifacts/run/raw_report.txt",
        changes_json_path=tmp_path / "artifacts/run/changes.json",
        changes_markdown_path=tmp_path / "artifacts/run/changes.md",
    )

    load_config_mock = Mock(return_value=config)
    prepare_workspace_mock = Mock(return_value=workspace)
    run_webchanges_mock = Mock(return_value=command_result)
    parse_output_mock = Mock(return_value=parsed_report)
    write_artifacts_mock = Mock(return_value=artifact_paths)
    notify_mock = Mock()

    monkeypatch.setattr(notebook, "load_monitor_config", load_config_mock)
    monkeypatch.setattr(notebook, "prepare_workspace", prepare_workspace_mock)
    monkeypatch.setattr(notebook, "run_webchanges", run_webchanges_mock)
    monkeypatch.setattr(notebook, "parse_webchanges_output", parse_output_mock)
    monkeypatch.setattr(notebook, "write_artifacts", write_artifacts_mock)
    monkeypatch.setattr(notebook, "notify_if_needed", notify_mock)

    with pytest.raises(RuntimeError, match="webchanges exited with code 2"):
        notebook.run_ir_webchanges_monitor.fn()

    write_artifacts_mock.assert_called_once()
    notify_mock.assert_not_called()

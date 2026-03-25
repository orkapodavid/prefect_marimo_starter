from pathlib import Path
from unittest.mock import Mock
import importlib
from types import SimpleNamespace

import pytest


def test_run_financial_monitor_daily_pipeline_calls_tasks_in_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    notebook = importlib.import_module("notebooks.financial_monitor.financial_monitor_daily_pipeline")
    call_order: list[str] = []

    config = object()
    runtime_paths = {
        "workspace_dir": tmp_path / "data/financial_monitor/prod",
        "reports_dir": tmp_path / "reports/financial_monitor/prod",
    }
    tdnet_candidates = [{"document_id": "tdnet-1"}]
    edinet_candidates = [{"document_id": "S100TEST"}]
    document_manifest = [{"document_id": "S100TEST", "xbrl_path": "sample.xbrl"}]
    extracted_metrics = [{"document_id": "S100TEST", "cash": 1200.0}]
    runway_metrics = [{"document_id": "S100TEST", "runway_months": 12.0}]
    intent_signals = [{"document_id": "S100TEST", "signals": []}]
    persisted_snapshot = {"filings_upserted": 1, "signals_upserted": 0}
    artifacts = {
        "markdown_path": str(tmp_path / "reports/financial_monitor/prod/run.md"),
        "json_path": str(tmp_path / "reports/financial_monitor/prod/run.json"),
    }

    load_config_mock = Mock(side_effect=lambda **kwargs: call_order.append("load") or config)
    resolve_paths_mock = Mock(
        side_effect=lambda **kwargs: call_order.append("paths") or runtime_paths
    )
    fetch_tdnet_mock = Mock(
        side_effect=lambda **kwargs: call_order.append("tdnet") or tdnet_candidates
    )
    fetch_edinet_mock = Mock(
        side_effect=lambda **kwargs: call_order.append("edinet") or edinet_candidates
    )
    download_docs_mock = Mock(
        side_effect=lambda **kwargs: call_order.append("download") or document_manifest
    )
    extract_metrics_mock = Mock(
        side_effect=lambda **kwargs: call_order.append("extract") or extracted_metrics
    )
    compute_runway_mock = Mock(
        side_effect=lambda **kwargs: call_order.append("runway") or runway_metrics
    )
    flag_intent_mock = Mock(
        side_effect=lambda **kwargs: call_order.append("intent") or intent_signals
    )
    persist_snapshot_mock = Mock(
        side_effect=lambda **kwargs: call_order.append("persist") or persisted_snapshot
    )
    write_artifacts_mock = Mock(
        side_effect=lambda **kwargs: call_order.append("artifacts") or artifacts
    )

    monkeypatch.setattr(notebook, "load_financial_monitor_config", load_config_mock)
    monkeypatch.setattr(notebook, "resolve_runtime_paths", resolve_paths_mock)
    monkeypatch.setattr(notebook, "fetch_tdnet_candidates", fetch_tdnet_mock)
    monkeypatch.setattr(notebook, "fetch_edinet_candidates", fetch_edinet_mock)
    monkeypatch.setattr(notebook, "download_source_documents", download_docs_mock)
    monkeypatch.setattr(notebook, "extract_cash_metrics", extract_metrics_mock)
    monkeypatch.setattr(notebook, "compute_cash_runway", compute_runway_mock)
    monkeypatch.setattr(notebook, "flag_management_intent", flag_intent_mock)
    monkeypatch.setattr(notebook, "persist_financial_snapshot", persist_snapshot_mock)
    monkeypatch.setattr(notebook, "write_financial_monitor_artifacts", write_artifacts_mock)

    result = notebook.run_financial_monitor_daily_pipeline.fn(
        config_path="./config/financial_monitor/financial_monitor_targets.yaml",
        filing_date="2026-03-25",
        environment="prod",
        dry_run=True,
    )

    assert call_order == [
        "load",
        "paths",
        "tdnet",
        "edinet",
        "download",
        "extract",
        "runway",
        "intent",
        "persist",
        "artifacts",
    ]
    assert result["persisted"] == persisted_snapshot
    assert result["artifacts"] == artifacts


def test_download_source_documents_uses_hardened_edinet_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    notebook = importlib.import_module("notebooks.financial_monitor.financial_monitor_daily_pipeline")
    calls: list[tuple[str, str]] = []

    class _FakeEdinetClient:
        def __init__(self, api_key: str):
            self.api_key = api_key

        def download_document(self, document_id: str, *, kind: str = "zip") -> bytes:
            calls.append((document_id, kind))
            return f"{document_id}:{kind}".encode("utf-8")

    monkeypatch.setattr(notebook, "resolve_edinet_api_key", lambda: "test-key")
    monkeypatch.setattr(notebook, "FinancialMonitorEdinetClient", _FakeEdinetClient)

    runtime_paths = {
        "workspace_dir": str(tmp_path / "data/financial_monitor/prod"),
        "reports_dir": str(tmp_path / "reports/financial_monitor/prod"),
    }
    manifest = notebook.download_source_documents.fn(
        runtime_paths=runtime_paths,
        tdnet_candidates=[],
        edinet_candidates=[
            {
                "document_id": "S100TEST",
                "description": "Quarterly Securities Report",
                "source_system": "edinet",
                "edinet_code": "E02529",
                "xbrl_download_url": "https://edinet.example/S100TEST?type=1",
                "pdf_download_url": "https://edinet.example/S100TEST?type=2",
            }
        ],
        dry_run=False,
    )

    assert calls == [("S100TEST", "zip"), ("S100TEST", "pdf")]
    assert len(manifest) == 2


def test_write_financial_monitor_artifacts_skips_prefect_artifact_outside_run_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    notebook = importlib.import_module("notebooks.financial_monitor.financial_monitor_daily_pipeline")
    create_artifact_mock = Mock()

    monkeypatch.setattr(
        notebook,
        "has_financial_monitor_prefect_run_context",
        lambda: False,
    )
    monkeypatch.setattr(notebook, "create_markdown_artifact", create_artifact_mock)

    runtime_paths = {
        "reports_dir": str(tmp_path / "reports/financial_monitor/dev"),
    }
    summary = {
        "environment": "dev",
        "filing_date": "2026-03-25",
        "tdnet_candidate_count": 0,
        "edinet_candidate_count": 0,
        "extracted_metric_count": 0,
        "persisted": {"filings_upserted": 0},
    }

    artifact_paths = notebook.write_financial_monitor_artifacts.fn(
        runtime_paths=runtime_paths,
        summary=summary,
        environment="dev",
    )

    create_artifact_mock.assert_not_called()
    assert Path(artifact_paths["markdown_path"]).exists()


def test_run_script_mode_entrypoint_uses_prefect_flow_when_tracked_config_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    notebook = importlib.import_module("notebooks.financial_monitor.financial_monitor_daily_pipeline")
    tracked_config_path = tmp_path / "financial_monitor_targets.yaml"
    tracked_config_path.write_text("targets: []\n", encoding="utf-8")

    monkeypatch.setattr(
        notebook,
        "SETTINGS",
        SimpleNamespace(financial_monitor_config_path=tracked_config_path),
    )
    flow_mock = Mock(return_value={"mode": "flow"})
    fallback_mock = Mock(return_value={"mode": "fallback"})
    monkeypatch.setattr(notebook, "run_financial_monitor_daily_pipeline", flow_mock)
    monkeypatch.setattr(notebook, "run_financial_monitor_script_fallback", fallback_mock)

    result = notebook.run_financial_monitor_script_entrypoint()

    flow_mock.assert_called_once_with(
        config_path=str(tracked_config_path),
        filing_date=None,
        environment="prod",
        dry_run=False,
    )
    fallback_mock.assert_not_called()
    assert result == {"mode": "flow"}

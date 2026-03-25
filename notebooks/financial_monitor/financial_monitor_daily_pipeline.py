# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "prefect>=3.0.0,<4.0.0",
#     "pydantic>=2.0.0",
#     "pydantic-settings>=2.0.0",
#     "pyyaml>=6.0",
#     "requests>=2.31.0",
#     "sqlalchemy>=2.0.0",
#     "lxml>=5.0.0",
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup:
    from datetime import datetime, date
    import json
    from pathlib import Path
    from zoneinfo import ZoneInfo

    import requests
    from prefect import flow, task
    from prefect.artifacts import create_markdown_artifact

    from services.financial_monitor.financial_monitor_artifacts import (
        write_financial_monitor_run_artifacts as write_financial_monitor_artifacts_service,
    )
    from services.financial_monitor.financial_monitor_cash_metrics import (
        compute_cash_runway as compute_cash_runway_service,
        compute_monthly_burn,
    )
    from services.financial_monitor.financial_monitor_config import (
        load_financial_monitor_config as load_financial_monitor_config_service,
    )
    from services.financial_monitor.financial_monitor_database import (
        create_financial_monitor_schema,
        get_financial_monitor_engine,
        get_financial_monitor_session,
        upsert_financial_snapshot,
    )
    from services.financial_monitor.financial_monitor_document_store import (
        ensure_document_store_dirs,
        write_source_document,
    )
    from services.financial_monitor.financial_monitor_edinet_client import (
        FinancialMonitorEdinetClient,
        resolve_edinet_api_key,
        select_tdnet_scoped_edinet_documents,
    )
    from services.financial_monitor.financial_monitor_intent_flags import (
        flag_management_intent as flag_management_intent_service,
    )
    from services.financial_monitor.financial_monitor_models import (
        FinancialMonitorCashMetricRecord,
        FinancialMonitorFilingRecord,
        FinancialMonitorIntentSignalRecord,
    )
    from services.financial_monitor.financial_monitor_tdnet_adapter import (
        fetch_tdnet_candidates as fetch_tdnet_candidates_service,
    )
    from services.financial_monitor.financial_monitor_xbrl_parser import (
        extract_cash_metrics_from_xbrl,
    )
    from shared_utils.config import get_settings
    from shared_utils.prefect_notifications import notify_on_failure

    SETTINGS = get_settings()




# ============================================================
# TASKS
# ============================================================


@app.function
@task(retries=2, retry_delay_seconds=30)
def load_financial_monitor_config(config_path: str):
    """Load and validate the financial monitor config file."""
    return load_financial_monitor_config_service(Path(config_path))


@app.function
@task(retries=2, retry_delay_seconds=30)
def resolve_runtime_paths(config, environment: str):
    """Resolve and create durable workspace paths."""
    workspace_dir = config.runtime.workspace_dir or (
        SETTINGS.financial_monitor_workspace_dir / environment
    )
    reports_dir = SETTINGS.financial_monitor_reports_dir / environment
    directories = ensure_document_store_dirs(workspace_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    return {
        "workspace_dir": str(workspace_dir),
        "reports_dir": str(reports_dir),
        "raw_dir": str(directories["raw_root"]),
        "manifests_dir": str(directories["manifests_dir"]),
    }


@app.function
@task(retries=2, retry_delay_seconds=30)
def fetch_tdnet_candidates(config, filing_date: str | None = None, dry_run: bool = False):
    """Fetch TDnet candidates for configured targets."""
    if dry_run:
        return []
    return [
        candidate.model_dump(mode="json")
        for candidate in fetch_tdnet_candidates_service(
            targets=config.targets,
            filing_date=resolve_financial_monitor_filing_date(filing_date),
        )
    ]


@app.function
@task(retries=2, retry_delay_seconds=30)
def fetch_edinet_candidates(
    config,
    tdnet_candidates: list[dict],
    filing_date: str | None = None,
    dry_run: bool = False,
):
    """Fetch EDINET documents matched to configured company registry entries."""
    if dry_run:
        return []
    client = FinancialMonitorEdinetClient(api_key=resolve_edinet_api_key())
    return [
        document.model_dump(mode="json")
        for document in select_tdnet_scoped_edinet_documents(
            documents=client.list_documents_by_date(
                resolve_financial_monitor_filing_date(filing_date)
            ),
            tdnet_candidates=tdnet_candidates,
            targets=config.targets,
        )
    ]


@app.function
@task(retries=2, retry_delay_seconds=30)
def download_source_documents(
    runtime_paths: dict,
    tdnet_candidates: list[dict],
    edinet_candidates: list[dict],
    dry_run: bool = False,
):
    """Download source documents into the feature workspace."""
    workspace_dir = Path(runtime_paths["workspace_dir"])
    manifest: list[dict] = []
    edinet_client = None
    if not dry_run:
        edinet_client = FinancialMonitorEdinetClient(api_key=resolve_edinet_api_key())

    for candidate in tdnet_candidates:
        for document_kind, url in (
            ("pdf", candidate.get("pdf_url")),
            ("xbrl", candidate.get("xbrl_url")),
        ):
            if not url:
                continue
            filename = Path(url).name or f"{candidate['company_code']}_{document_kind}"
            local_path = workspace_dir / "raw" / "tdnet" / candidate["company_code"] / filename
            if not dry_run:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                local_path = write_source_document(
                    workspace_dir=workspace_dir,
                    source="tdnet",
                    document_id=candidate["company_code"],
                    filename=filename,
                    content=response.content,
                )
            manifest.append(
                {
                    "document_id": candidate["company_code"],
                    "source_system": "tdnet",
                    "document_kind": document_kind,
                    "local_path": str(local_path),
                    "title": candidate["title"],
                    "source_url": url,
                    "edinet_code": candidate.get("edinet_code", ""),
                }
            )

    for document in edinet_candidates:
        for document_kind, download_kind, url in (
            ("xbrl", "zip", document.get("xbrl_download_url")),
            ("pdf", "pdf", document.get("pdf_download_url")),
            ("csv", "csv", document.get("csv_download_url")),
        ):
            if not url:
                continue
            suffix = ".zip" if document_kind == "xbrl" else f".{document_kind}"
            filename = f"{document['document_id']}{suffix}"
            local_path = workspace_dir / "raw" / "edinet" / document["document_id"] / filename
            if not dry_run:
                payload = edinet_client.download_document(
                    document["document_id"],
                    kind=download_kind,
                )
                local_path = write_source_document(
                    workspace_dir=workspace_dir,
                    source="edinet",
                    document_id=document["document_id"],
                    filename=filename,
                    content=payload,
                )
            manifest.append(
                {
                    "document_id": document["document_id"],
                    "source_system": "edinet",
                    "document_kind": document_kind,
                    "local_path": str(local_path),
                    "title": document["description"],
                    "source_url": url,
                    "edinet_code": document["edinet_code"],
                }
            )

    return manifest


@app.function
@task(retries=2, retry_delay_seconds=30)
def extract_cash_metrics(document_manifest: list[dict]):
    """Parse downloaded EDINET XBRL files into cash-metric records."""
    extracted_metrics: list[dict] = []
    for document in document_manifest:
        if document["source_system"] != "edinet" or document["document_kind"] != "xbrl":
            continue
        local_path = Path(document["local_path"])
        if not local_path.exists():
            continue
        metrics = extract_cash_metrics_from_xbrl(local_path)
        extracted_metrics.append(
            {
                "document_id": document["document_id"],
                "cash_metric": metrics.model_dump(mode="json"),
            }
        )
    return extracted_metrics


@app.function
@task(retries=2, retry_delay_seconds=30)
def compute_cash_runway(extracted_metrics: list[dict]):
    """Compute deterministic monthly burn and cash runway from extracted metrics."""
    enriched_metrics: list[dict] = []
    for extracted_metric in extracted_metrics:
        metric = FinancialMonitorCashMetricRecord.model_validate(extracted_metric["cash_metric"])
        monthly_burn = metric.monthly_burn or compute_monthly_burn(
            operating_cash_flow=metric.operating_cash_flow
        )
        runway_months = compute_cash_runway_service(
            cash=metric.cash,
            monthly_burn=monthly_burn,
        )
        enriched_metrics.append(
            {
                "document_id": extracted_metric["document_id"],
                "cash_metric": metric.model_copy(
                    update={
                        "monthly_burn": monthly_burn,
                        "runway_months": runway_months,
                    }
                ).model_dump(mode="json"),
            }
        )
    return enriched_metrics


@app.function
@task(retries=2, retry_delay_seconds=30)
def flag_management_intent(tdnet_candidates: list[dict], edinet_candidates: list[dict]):
    """Flag deterministic fundraising and liquidity language."""
    tdnet_titles_by_edinet_code: dict[str, list[str]] = {}
    for candidate in tdnet_candidates:
        edinet_code = candidate.get("edinet_code", "")
        tdnet_titles_by_edinet_code.setdefault(edinet_code, []).append(candidate["title"])

    flagged_documents: list[dict] = []
    for document in edinet_candidates:
        text = "\n".join(
            [document["description"], *tdnet_titles_by_edinet_code.get(document["edinet_code"], [])]
        ).strip()
        signals = flag_management_intent_service(text=text)
        flagged_documents.append(
            {
                "document_id": document["document_id"],
                "signals": [signal.model_dump(mode="json") for signal in signals],
            }
        )
    return flagged_documents


@app.function
@task(retries=2, retry_delay_seconds=30)
def persist_financial_snapshot(
    config,
    edinet_candidates: list[dict],
    runway_metrics: list[dict],
    intent_signal_batches: list[dict],
    dry_run: bool = False,
):
    """Upsert normalized filing, metric, and intent-signal records."""
    if dry_run:
        return {
            "filings_upserted": len(edinet_candidates),
            "metrics_upserted": len(runway_metrics),
            "signals_upserted": sum(len(batch["signals"]) for batch in intent_signal_batches),
            "dry_run": True,
        }

    engine = get_financial_monitor_engine()
    create_financial_monitor_schema(engine)
    session_factory = get_financial_monitor_session(engine=engine)
    metrics_by_document_id = {
        item["document_id"]: FinancialMonitorCashMetricRecord.model_validate(item["cash_metric"])
        for item in runway_metrics
    }
    targets_by_edinet_code = {
        target.edinet_code: target for target in config.targets if target.edinet_code
    }
    signals_by_document_id = {
        item["document_id"]: [
            FinancialMonitorIntentSignalRecord.model_validate(signal)
            for signal in item["signals"]
        ]
        for item in intent_signal_batches
    }

    filings_upserted = 0
    metrics_upserted = 0
    signals_upserted = 0

    with session_factory.begin() as session:
        for document in edinet_candidates:
            target = targets_by_edinet_code.get(document["edinet_code"])
            if target is None:
                continue
            filing_record = FinancialMonitorFilingRecord(
                company_id=target.company_id,
                company_code=target.ticker.split(".", 1)[0],
                company_name=target.company_name,
                exchange=target.exchange,
                edinet_code=target.edinet_code,
                source_system=document["source_system"],
                document_id=document["document_id"],
                filing_date=date.fromisoformat(document["filed_at"][:10]),
                title=document["description"],
                source_url=document["xbrl_download_url"] or document["pdf_download_url"] or "",
            )
            cash_metric = metrics_by_document_id.get(
                document["document_id"],
                FinancialMonitorCashMetricRecord(),
            )
            intent_signals = signals_by_document_id.get(document["document_id"], [])
            upsert_financial_snapshot(
                session=session,
                filing=filing_record,
                cash_metric=cash_metric,
                intent_signals=intent_signals,
            )
            filings_upserted += 1
            if document["document_id"] in metrics_by_document_id:
                metrics_upserted += 1
            signals_upserted += len(intent_signals)

    return {
        "filings_upserted": filings_upserted,
        "metrics_upserted": metrics_upserted,
        "signals_upserted": signals_upserted,
        "dry_run": False,
    }


@app.function
@task(retries=2, retry_delay_seconds=30)
def write_financial_monitor_artifacts(runtime_paths: dict, summary: dict, environment: str):
    """Write JSON/Markdown artifacts and register a Prefect markdown artifact."""
    run_label = datetime.now(ZoneInfo(SETTINGS.financial_monitor_report_timezone)).isoformat(
        timespec="seconds"
    ).replace(":", "-")
    artifact_paths = write_financial_monitor_artifacts_service(
        reports_dir=Path(runtime_paths["reports_dir"]),
        run_label=run_label,
        summary=summary,
    )
    if has_financial_monitor_prefect_run_context():
        try:
            create_markdown_artifact(
                markdown=artifact_paths["summary_markdown_path"].read_text(encoding="utf-8"),
                key=f"financial-monitor-summary-{environment}",
                description=f"Financial monitor summary for {run_label}",
            )
        except Exception:
            pass
    return {
        "run_dir": str(artifact_paths["run_dir"]),
        "json_path": str(artifact_paths["summary_json_path"]),
        "markdown_path": str(artifact_paths["summary_markdown_path"]),
    }


@app.function
def has_financial_monitor_prefect_run_context() -> bool:
    try:
        from prefect.context import get_run_context

        get_run_context()
    except Exception:
        return False
    return True


@app.function
def resolve_financial_monitor_filing_date(filing_date: str | None) -> date:
    if filing_date:
        return date.fromisoformat(filing_date)
    return datetime.now(ZoneInfo(SETTINGS.financial_monitor_timezone)).date()


@app.function
def invoke_financial_monitor_pipeline_step(step, *, use_task_bodies: bool, **kwargs):
    if use_task_bodies and hasattr(step, "fn"):
        return step.fn(**kwargs)
    return step(**kwargs)


@app.function
def build_financial_monitor_pipeline_summary(
    *,
    config_path: str,
    environment: str,
    filing_date: str | None,
    runtime_paths: dict,
    tdnet_candidates: list[dict],
    edinet_candidates: list[dict],
    document_manifest: list[dict],
    runway_metrics: list[dict],
    persisted: dict,
    dry_run: bool,
) -> dict:
    return {
        "environment": environment,
        "config_path": config_path,
        "filing_date": resolve_financial_monitor_filing_date(filing_date).isoformat(),
        "workspace_dir": runtime_paths["workspace_dir"],
        "reports_dir": runtime_paths["reports_dir"],
        "tdnet_candidate_count": len(tdnet_candidates),
        "edinet_candidate_count": len(edinet_candidates),
        "document_manifest_count": len(document_manifest),
        "extracted_metric_count": len(runway_metrics),
        "persisted": persisted,
        "dry_run": dry_run,
    }


@app.function
def run_financial_monitor_pipeline_steps(
    *,
    step_load_config,
    step_resolve_runtime_paths,
    step_fetch_tdnet_candidates,
    step_fetch_edinet_candidates,
    step_download_source_documents,
    step_extract_cash_metrics,
    step_compute_cash_runway,
    step_flag_management_intent,
    step_persist_financial_snapshot,
    step_write_artifacts,
    config_path: str,
    filing_date: str | None,
    environment: str,
    dry_run: bool,
    use_task_bodies: bool = False,
) -> dict:
    config = invoke_financial_monitor_pipeline_step(
        step_load_config,
        use_task_bodies=use_task_bodies,
        config_path=config_path,
    )
    runtime_paths = invoke_financial_monitor_pipeline_step(
        step_resolve_runtime_paths,
        use_task_bodies=use_task_bodies,
        config=config,
        environment=environment,
    )
    tdnet_candidates = invoke_financial_monitor_pipeline_step(
        step_fetch_tdnet_candidates,
        use_task_bodies=use_task_bodies,
        config=config,
        filing_date=filing_date,
        dry_run=dry_run,
    )
    edinet_candidates = invoke_financial_monitor_pipeline_step(
        step_fetch_edinet_candidates,
        use_task_bodies=use_task_bodies,
        config=config,
        tdnet_candidates=tdnet_candidates,
        filing_date=filing_date,
        dry_run=dry_run,
    )
    document_manifest = invoke_financial_monitor_pipeline_step(
        step_download_source_documents,
        use_task_bodies=use_task_bodies,
        runtime_paths=runtime_paths,
        tdnet_candidates=tdnet_candidates,
        edinet_candidates=edinet_candidates,
        dry_run=dry_run,
    )
    extracted_metrics = invoke_financial_monitor_pipeline_step(
        step_extract_cash_metrics,
        use_task_bodies=use_task_bodies,
        document_manifest=document_manifest,
    )
    runway_metrics = invoke_financial_monitor_pipeline_step(
        step_compute_cash_runway,
        use_task_bodies=use_task_bodies,
        extracted_metrics=extracted_metrics,
    )
    intent_signal_batches = invoke_financial_monitor_pipeline_step(
        step_flag_management_intent,
        use_task_bodies=use_task_bodies,
        tdnet_candidates=tdnet_candidates,
        edinet_candidates=edinet_candidates,
    )
    persisted = invoke_financial_monitor_pipeline_step(
        step_persist_financial_snapshot,
        use_task_bodies=use_task_bodies,
        config=config,
        edinet_candidates=edinet_candidates,
        runway_metrics=runway_metrics,
        intent_signal_batches=intent_signal_batches,
        dry_run=dry_run,
    )
    summary = build_financial_monitor_pipeline_summary(
        config_path=config_path,
        environment=environment,
        filing_date=filing_date,
        runtime_paths=runtime_paths,
        tdnet_candidates=tdnet_candidates,
        edinet_candidates=edinet_candidates,
        document_manifest=document_manifest,
        runway_metrics=runway_metrics,
        persisted=persisted,
        dry_run=dry_run,
    )
    artifacts = invoke_financial_monitor_pipeline_step(
        step_write_artifacts,
        use_task_bodies=use_task_bodies,
        runtime_paths=runtime_paths,
        summary=summary,
        environment=environment,
    )
    summary["artifacts"] = artifacts
    return summary

# ============================================================
# FLOW
# ============================================================


@app.function
@flow(name="financial-monitor-daily-pipeline", log_prints=True, on_failure=[notify_on_failure])
def run_financial_monitor_daily_pipeline(
    config_path: str = "./config/financial_monitor/financial_monitor_targets.yaml",
    filing_date: str | None = None,
    environment: str = "prod",
    dry_run: bool = False,
) -> dict:
    """Monitor configured Japanese companies for cash-relevant disclosures."""
    return run_financial_monitor_pipeline_steps(
        step_load_config=load_financial_monitor_config,
        step_resolve_runtime_paths=resolve_runtime_paths,
        step_fetch_tdnet_candidates=fetch_tdnet_candidates,
        step_fetch_edinet_candidates=fetch_edinet_candidates,
        step_download_source_documents=download_source_documents,
        step_extract_cash_metrics=extract_cash_metrics,
        step_compute_cash_runway=compute_cash_runway,
        step_flag_management_intent=flag_management_intent,
        step_persist_financial_snapshot=persist_financial_snapshot,
        step_write_artifacts=write_financial_monitor_artifacts,
        config_path=config_path,
        filing_date=filing_date,
        environment=environment,
        dry_run=dry_run,
    )


@app.function
def run_financial_monitor_script_fallback(
    config_path: Path,
    *,
    environment: str,
) -> dict:
    return run_financial_monitor_pipeline_steps(
        step_load_config=load_financial_monitor_config,
        step_resolve_runtime_paths=resolve_runtime_paths,
        step_fetch_tdnet_candidates=fetch_tdnet_candidates,
        step_fetch_edinet_candidates=fetch_edinet_candidates,
        step_download_source_documents=download_source_documents,
        step_extract_cash_metrics=extract_cash_metrics,
        step_compute_cash_runway=compute_cash_runway,
        step_flag_management_intent=flag_management_intent,
        step_persist_financial_snapshot=persist_financial_snapshot,
        step_write_artifacts=write_financial_monitor_artifacts,
        config_path=str(config_path),
        filing_date=None,
        environment=environment,
        dry_run=True,
        use_task_bodies=True,
    )


@app.function
def run_financial_monitor_script_entrypoint() -> dict:
    tracked_config_path = SETTINGS.financial_monitor_config_path
    if tracked_config_path.exists():
        return run_financial_monitor_daily_pipeline(
            config_path=str(tracked_config_path),
            filing_date=None,
            environment="prod",
            dry_run=False,
        )

    example_config_path = tracked_config_path.with_name("financial_monitor_targets.example.yaml")
    return run_financial_monitor_script_fallback(
        config_path=example_config_path,
        environment="dev",
    )

# ============================================================
# INTERACTIVE CELLS (edit mode only)
# ============================================================


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    config_path_input = None
    filing_date_input = None
    environment_select = None
    dry_run_toggle = None
    run_button = None
    ui = None

    if mo.app_meta().mode == "edit":
        default_config_path = (
            SETTINGS.financial_monitor_config_path
            if SETTINGS.financial_monitor_config_path.exists()
            else SETTINGS.financial_monitor_config_path.with_name(
                "financial_monitor_targets.example.yaml"
            )
        )
        config_path_input = mo.ui.text(
            value=str(default_config_path),
            label="Config Path",
            full_width=True,
        )
        filing_date_input = mo.ui.text(value="", label="Filing Date (YYYY-MM-DD)")
        environment_select = mo.ui.dropdown(
            options=["dev", "prod"],
            value="dev",
            label="Environment",
        )
        dry_run_toggle = mo.ui.checkbox(label="Dry Run", value=True)
        run_button = mo.ui.run_button(label="Run Financial Monitor")
        ui = mo.vstack(
            [
                config_path_input,
                filing_date_input,
                environment_select,
                dry_run_toggle,
                run_button,
            ]
        )

    ui
    return (
        config_path_input,
        filing_date_input,
        environment_select,
        dry_run_toggle,
        run_button,
    )


@app.cell
def _(
    config_path_input,
    dry_run_toggle,
    environment_select,
    filing_date_input,
    mo,
    run_button,
):
    interactive_result = None

    if mo.app_meta().mode == "edit" and run_button and run_button.value:
        interactive_result = run_financial_monitor_daily_pipeline(
            config_path=config_path_input.value,
            filing_date=filing_date_input.value or None,
            environment=environment_select.value,
            dry_run=bool(dry_run_toggle.value),
        )

    return (interactive_result,)


@app.cell
def _(interactive_result, mo):
    preview_view = None

    if mo.app_meta().mode == "edit":
        preview_view = mo.md(
            "No manual run has been triggered yet."
            if interactive_result is None
            else f"```json\n{json.dumps(interactive_result, ensure_ascii=False, indent=2)}\n```"
        )

    preview_view
    return


# ============================================================
# SCRIPT EXECUTION (production)
# ============================================================


@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        result = run_financial_monitor_script_entrypoint()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return


if __name__ == "__main__":
    app.run()

from datetime import date

from sqlalchemy import create_engine, func, select

from services.financial_monitor.financial_monitor_database import (
    FINANCIAL_MONITOR_METADATA,
    create_financial_monitor_schema,
    get_financial_monitor_session,
    tbl_financial_monitor_cash_metrics,
    tbl_financial_monitor_filings,
    tbl_financial_monitor_intent_signals,
    upsert_financial_snapshot,
)
from services.financial_monitor.financial_monitor_models import (
    FinancialMonitorCashMetricRecord,
    FinancialMonitorFilingRecord,
    FinancialMonitorIntentSignalRecord,
)


def test_financial_monitor_table_names_follow_repo_conventions():
    table_names = set(FINANCIAL_MONITOR_METADATA.tables)

    assert "tblFinancialMonitorCompanies" in table_names
    assert "tblFinancialMonitorFilings" in table_names
    assert "tblFinancialMonitorCashMetrics" in table_names
    assert "tblFinancialMonitorIntentSignals" in table_names


def test_financial_monitor_indexes_follow_repo_conventions():
    filing_index_names = {index.name for index in tbl_financial_monitor_filings.indexes}
    assert "idxTblFinancialMonitorFilingsCompanyCodeFilingDate" in filing_index_names
    assert "idxTblFinancialMonitorFilingsDocumentId" in filing_index_names

    cash_metric_index_names = {
        index.name for index in tbl_financial_monitor_cash_metrics.indexes
    }
    assert "idxTblFinancialMonitorCashMetricsFilingId" in cash_metric_index_names

    intent_signal_index_names = {
        index.name for index in tbl_financial_monitor_intent_signals.indexes
    }
    assert "idxTblFinancialMonitorIntentSignalsFilingIdSignalType" in intent_signal_index_names


def test_upsert_financial_snapshot_is_idempotent():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_financial_monitor_schema(engine)
    session_factory = get_financial_monitor_session(engine=engine)

    filing = FinancialMonitorFilingRecord(
        company_id="mitsubishi_corp",
        company_code="8058",
        company_name="Mitsubishi Corporation",
        exchange="TSE",
        edinet_code="E02529",
        source_system="edinet",
        document_id="S100TEST",
        filing_date=date(2026, 3, 25),
        title="Quarterly Securities Report",
        source_url="https://edinet.example/S100TEST",
    )
    cash_metric = FinancialMonitorCashMetricRecord(
        period_end=date(2025, 12, 31),
        currency="JPY",
        cash=1200,
        operating_cash_flow=-1200,
        investing_cash_flow=-300,
        financing_cash_flow=500,
        monthly_burn=100,
        runway_months=12,
        tag_names={"cash": "jpdei_cor:CashAndDeposits"},
    )
    intent_signals = [
        FinancialMonitorIntentSignalRecord(
            signal_type="fundraising",
            matched_phrase="第三者割当",
            excerpt="第三者割当による資金調達を実施",
            source_section="management_commentary",
            match_rule="phrase:fundraising:third_party_allotment",
        )
    ]

    with session_factory.begin() as session:
        upsert_financial_snapshot(
            session=session,
            filing=filing,
            cash_metric=cash_metric,
            intent_signals=intent_signals,
        )

    with session_factory.begin() as session:
        upsert_financial_snapshot(
            session=session,
            filing=filing,
            cash_metric=cash_metric,
            intent_signals=intent_signals,
        )

    with session_factory() as session:
        filing_count = session.execute(select(func.count()).select_from(tbl_financial_monitor_filings)).scalar_one()
        cash_metric_count = session.execute(
            select(func.count()).select_from(tbl_financial_monitor_cash_metrics)
        ).scalar_one()
        intent_signal_count = session.execute(
            select(func.count()).select_from(tbl_financial_monitor_intent_signals)
        ).scalar_one()

    assert filing_count == 1
    assert cash_metric_count == 1
    assert intent_signal_count == 1

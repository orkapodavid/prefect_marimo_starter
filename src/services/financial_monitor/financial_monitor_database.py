"""Database helpers and schema metadata for financial monitor."""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Engine,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.orm import Session, sessionmaker

from services.financial_monitor.financial_monitor_models import (
    FinancialMonitorCashMetricRecord,
    FinancialMonitorFilingRecord,
    FinancialMonitorIntentSignalRecord,
)
from shared_utils.config import get_settings

FINANCIAL_MONITOR_METADATA = MetaData()

tbl_financial_monitor_companies = Table(
    "tblFinancialMonitorCompanies",
    FINANCIAL_MONITOR_METADATA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("company_id", Text, nullable=False),
    Column("company_code", String(16), nullable=False, unique=True),
    Column("company_name", Text, nullable=False),
    Column("exchange", String(32), nullable=False, default=""),
    Column("edinet_code", String(16), nullable=False, default=""),
    Column("active", Boolean, nullable=False, default=True),
)

tbl_financial_monitor_filings = Table(
    "tblFinancialMonitorFilings",
    FINANCIAL_MONITOR_METADATA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "company_pk",
        Integer,
        ForeignKey("tblFinancialMonitorCompanies.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("company_code", String(16), nullable=False),
    Column("source_system", String(32), nullable=False),
    Column("document_id", String(64), nullable=False, unique=True),
    Column("filing_date", Date, nullable=False),
    Column("title", Text, nullable=False),
    Column("source_url", Text, nullable=False),
    Column("local_raw_path", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
Index(
    "idxTblFinancialMonitorFilingsCompanyCodeFilingDate",
    tbl_financial_monitor_filings.c.company_code,
    tbl_financial_monitor_filings.c.filing_date,
)
Index(
    "idxTblFinancialMonitorFilingsDocumentId",
    tbl_financial_monitor_filings.c.document_id,
    unique=True,
)

tbl_financial_monitor_cash_metrics = Table(
    "tblFinancialMonitorCashMetrics",
    FINANCIAL_MONITOR_METADATA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "filing_id",
        Integer,
        ForeignKey("tblFinancialMonitorFilings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    ),
    Column("period_end", Date, nullable=True),
    Column("currency", String(16), nullable=False, default="JPY"),
    Column("cash", Numeric(18, 2), nullable=True),
    Column("operating_cash_flow", Numeric(18, 2), nullable=True),
    Column("investing_cash_flow", Numeric(18, 2), nullable=True),
    Column("financing_cash_flow", Numeric(18, 2), nullable=True),
    Column("monthly_burn", Numeric(18, 2), nullable=True),
    Column("runway_months", Numeric(18, 2), nullable=True),
    Column("tag_names", JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
Index(
    "idxTblFinancialMonitorCashMetricsFilingId",
    tbl_financial_monitor_cash_metrics.c.filing_id,
    unique=True,
)

tbl_financial_monitor_intent_signals = Table(
    "tblFinancialMonitorIntentSignals",
    FINANCIAL_MONITOR_METADATA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "filing_id",
        Integer,
        ForeignKey("tblFinancialMonitorFilings.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("signal_type", String(32), nullable=False),
    Column("matched_phrase", Text, nullable=False),
    Column("excerpt", Text, nullable=False),
    Column("source_section", String(64), nullable=False),
    Column("match_rule", String(128), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
Index(
    "idxTblFinancialMonitorIntentSignalsFilingIdSignalType",
    tbl_financial_monitor_intent_signals.c.filing_id,
    tbl_financial_monitor_intent_signals.c.signal_type,
)


def get_financial_monitor_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for the financial monitor database."""
    resolved_database_url = database_url or get_settings().financial_monitor_database_url
    return create_engine(resolved_database_url, future=True)


def get_financial_monitor_session(
    engine: Engine | None = None,
    database_url: str | None = None,
) -> sessionmaker[Session]:
    """Create a configured SQLAlchemy session factory."""
    resolved_engine = engine or get_financial_monitor_engine(database_url=database_url)
    return sessionmaker(bind=resolved_engine, expire_on_commit=False, future=True)


def create_financial_monitor_schema(engine: Engine) -> None:
    """Create all financial monitor tables on an engine."""
    FINANCIAL_MONITOR_METADATA.create_all(engine)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _upsert_company(session: Session, filing: FinancialMonitorFilingRecord) -> int:
    company_row = session.execute(
        select(tbl_financial_monitor_companies).where(
            tbl_financial_monitor_companies.c.company_code == filing.company_code
        )
    ).mappings().first()
    if company_row is None:
        result = session.execute(
            insert(tbl_financial_monitor_companies).values(
                company_id=filing.company_id,
                company_code=filing.company_code,
                company_name=filing.company_name,
                exchange=filing.exchange,
                edinet_code=filing.edinet_code,
                active=True,
            )
        )
        return int(result.inserted_primary_key[0])

    session.execute(
        update(tbl_financial_monitor_companies)
        .where(tbl_financial_monitor_companies.c.id == company_row["id"])
        .values(
            company_id=filing.company_id,
            company_name=filing.company_name,
            exchange=filing.exchange,
            edinet_code=filing.edinet_code,
            active=True,
        )
    )
    return int(company_row["id"])


def _upsert_filing(session: Session, filing: FinancialMonitorFilingRecord, company_pk: int) -> int:
    timestamp = _now()
    filing_row = session.execute(
        select(tbl_financial_monitor_filings).where(
            tbl_financial_monitor_filings.c.document_id == filing.document_id
        )
    ).mappings().first()
    if filing_row is None:
        result = session.execute(
            insert(tbl_financial_monitor_filings).values(
                company_pk=company_pk,
                company_code=filing.company_code,
                source_system=filing.source_system,
                document_id=filing.document_id,
                filing_date=filing.filing_date,
                title=filing.title,
                source_url=filing.source_url,
                local_raw_path=filing.local_raw_path,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )
        return int(result.inserted_primary_key[0])

    session.execute(
        update(tbl_financial_monitor_filings)
        .where(tbl_financial_monitor_filings.c.id == filing_row["id"])
        .values(
            company_pk=company_pk,
            company_code=filing.company_code,
            source_system=filing.source_system,
            filing_date=filing.filing_date,
            title=filing.title,
            source_url=filing.source_url,
            local_raw_path=filing.local_raw_path,
            updated_at=timestamp,
        )
    )
    return int(filing_row["id"])


def _upsert_cash_metric(
    session: Session,
    filing_id: int,
    cash_metric: FinancialMonitorCashMetricRecord,
) -> None:
    timestamp = _now()
    metric_row = session.execute(
        select(tbl_financial_monitor_cash_metrics).where(
            tbl_financial_monitor_cash_metrics.c.filing_id == filing_id
        )
    ).mappings().first()
    values = {
        "filing_id": filing_id,
        "period_end": cash_metric.period_end,
        "currency": cash_metric.currency,
        "cash": cash_metric.cash,
        "operating_cash_flow": cash_metric.operating_cash_flow,
        "investing_cash_flow": cash_metric.investing_cash_flow,
        "financing_cash_flow": cash_metric.financing_cash_flow,
        "monthly_burn": cash_metric.monthly_burn,
        "runway_months": cash_metric.runway_months,
        "tag_names": cash_metric.tag_names,
        "updated_at": timestamp,
    }
    if metric_row is None:
        session.execute(
            insert(tbl_financial_monitor_cash_metrics).values(
                **values,
                created_at=timestamp,
            )
        )
        return

    session.execute(
        update(tbl_financial_monitor_cash_metrics)
        .where(tbl_financial_monitor_cash_metrics.c.id == metric_row["id"])
        .values(**values)
    )


def _replace_intent_signals(
    session: Session,
    filing_id: int,
    intent_signals: list[FinancialMonitorIntentSignalRecord],
) -> None:
    session.execute(
        delete(tbl_financial_monitor_intent_signals).where(
            tbl_financial_monitor_intent_signals.c.filing_id == filing_id
        )
    )
    timestamp = _now()
    for signal in intent_signals:
        session.execute(
            insert(tbl_financial_monitor_intent_signals).values(
                filing_id=filing_id,
                signal_type=signal.signal_type,
                matched_phrase=signal.matched_phrase,
                excerpt=signal.excerpt,
                source_section=signal.source_section,
                match_rule=signal.match_rule,
                created_at=timestamp,
            )
        )


def upsert_financial_snapshot(
    session: Session,
    filing: FinancialMonitorFilingRecord,
    cash_metric: FinancialMonitorCashMetricRecord,
    intent_signals: list[FinancialMonitorIntentSignalRecord],
) -> int:
    """Upsert a financial snapshot and replace dependent rows deterministically."""
    company_pk = _upsert_company(session=session, filing=filing)
    filing_id = _upsert_filing(session=session, filing=filing, company_pk=company_pk)
    _upsert_cash_metric(session=session, filing_id=filing_id, cash_metric=cash_metric)
    _replace_intent_signals(
        session=session,
        filing_id=filing_id,
        intent_signals=intent_signals,
    )
    return filing_id

"""Create financial monitor schema."""

from alembic import op
import sqlalchemy as sa

revision = "202603250002"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tblFinancialMonitorCompanies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Text(), nullable=False),
        sa.Column("company_code", sa.String(length=16), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("edinet_code", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_code"),
    )

    op.create_table(
        "tblFinancialMonitorFilings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_pk", sa.Integer(), nullable=False),
        sa.Column("company_code", sa.String(length=16), nullable=False),
        sa.Column("source_system", sa.String(length=32), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("local_raw_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_pk"], ["tblFinancialMonitorCompanies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index(
        "idxTblFinancialMonitorFilingsCompanyCodeFilingDate",
        "tblFinancialMonitorFilings",
        ["company_code", "filing_date"],
        unique=False,
    )
    op.create_index(
        "idxTblFinancialMonitorFilingsDocumentId",
        "tblFinancialMonitorFilings",
        ["document_id"],
        unique=True,
    )

    op.create_table(
        "tblFinancialMonitorCashMetrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filing_id", sa.Integer(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=False, server_default="JPY"),
        sa.Column("cash", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("operating_cash_flow", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("investing_cash_flow", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("financing_cash_flow", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("monthly_burn", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("runway_months", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("tag_names", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["filing_id"], ["tblFinancialMonitorFilings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("filing_id"),
    )
    op.create_index(
        "idxTblFinancialMonitorCashMetricsFilingId",
        "tblFinancialMonitorCashMetrics",
        ["filing_id"],
        unique=True,
    )

    op.create_table(
        "tblFinancialMonitorIntentSignals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filing_id", sa.Integer(), nullable=False),
        sa.Column("signal_type", sa.String(length=32), nullable=False),
        sa.Column("matched_phrase", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("source_section", sa.String(length=64), nullable=False),
        sa.Column("match_rule", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["filing_id"], ["tblFinancialMonitorFilings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idxTblFinancialMonitorIntentSignalsFilingIdSignalType",
        "tblFinancialMonitorIntentSignals",
        ["filing_id", "signal_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idxTblFinancialMonitorIntentSignalsFilingIdSignalType",
        table_name="tblFinancialMonitorIntentSignals",
    )
    op.drop_table("tblFinancialMonitorIntentSignals")
    op.drop_index(
        "idxTblFinancialMonitorCashMetricsFilingId",
        table_name="tblFinancialMonitorCashMetrics",
    )
    op.drop_table("tblFinancialMonitorCashMetrics")
    op.drop_index(
        "idxTblFinancialMonitorFilingsDocumentId",
        table_name="tblFinancialMonitorFilings",
    )
    op.drop_index(
        "idxTblFinancialMonitorFilingsCompanyCodeFilingDate",
        table_name="tblFinancialMonitorFilings",
    )
    op.drop_table("tblFinancialMonitorFilings")
    op.drop_table("tblFinancialMonitorCompanies")

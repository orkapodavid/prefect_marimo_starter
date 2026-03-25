from datetime import date
from pathlib import Path

from services.financial_monitor.financial_monitor_xbrl_parser import (
    extract_cash_metrics_from_xbrl,
)


def test_extract_cash_metrics_reads_expected_xbrl_tags(
    financial_monitor_fixtures_dir: Path,
):
    xbrl_path = financial_monitor_fixtures_dir / "xbrl/cash_metrics_sample.xbrl"

    metrics = extract_cash_metrics_from_xbrl(
        xbrl_path=xbrl_path,
        period_end=date(2025, 12, 31),
    )

    assert metrics.period_end == date(2025, 12, 31)
    assert metrics.cash == 1200.0
    assert metrics.operating_cash_flow == -1200.0
    assert metrics.investing_cash_flow == -300.0
    assert metrics.financing_cash_flow == 500.0
    assert metrics.tag_names == {
        "cash": "jpdei_cor:CashAndDeposits",
        "operating_cash_flow": "jppfs_cor:NetCashProvidedByUsedInOperatingActivities",
        "investing_cash_flow": "jppfs_cor:NetCashProvidedByUsedInInvestingActivities",
        "financing_cash_flow": "jppfs_cor:NetCashProvidedByUsedInFinancingActivities",
    }


def test_extract_cash_metrics_prefers_current_consolidated_contexts(tmp_path: Path):
    xbrl_path = tmp_path / "context_priority_sample.xbrl"
    xbrl_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xbrli:xbrl
  xmlns:xbrli="http://www.xbrl.org/2003/instance"
  xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
  xmlns:jpdei_cor="http://example.com/jpdei_cor"
  xmlns:jppfs_cor="http://example.com/jppfs_cor"
  xmlns:jpcrp_cor="http://example.com/jpcrp_cor">
  <xbrli:context id="PriorYearInstant">
    <xbrli:entity><xbrli:identifier scheme="test">entity</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>
  </xbrli:context>
  <xbrli:context id="CurrentYearInstant_NonConsolidatedMember">
    <xbrli:entity>
      <xbrli:identifier scheme="test">entity</xbrli:identifier>
      <xbrli:segment>
        <xbrldi:explicitMember dimension="jpcrp_cor:ReportingEntityAxis">jpcrp_cor:NonConsolidatedMember</xbrldi:explicitMember>
      </xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period>
  </xbrli:context>
  <xbrli:context id="CurrentYearInstant">
    <xbrli:entity><xbrli:identifier scheme="test">entity</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period>
  </xbrli:context>
  <xbrli:context id="PriorYearDuration">
    <xbrli:entity><xbrli:identifier scheme="test">entity</xbrli:identifier></xbrli:entity>
    <xbrli:period>
      <xbrli:startDate>2024-01-01</xbrli:startDate>
      <xbrli:endDate>2024-12-31</xbrli:endDate>
    </xbrli:period>
  </xbrli:context>
  <xbrli:context id="CurrentYearDuration">
    <xbrli:entity><xbrli:identifier scheme="test">entity</xbrli:identifier></xbrli:entity>
    <xbrli:period>
      <xbrli:startDate>2025-01-01</xbrli:startDate>
      <xbrli:endDate>2025-12-31</xbrli:endDate>
    </xbrli:period>
  </xbrli:context>
  <jpdei_cor:CashAndDeposits contextRef="PriorYearInstant">900</jpdei_cor:CashAndDeposits>
  <jpdei_cor:CashAndDeposits contextRef="CurrentYearInstant_NonConsolidatedMember">800</jpdei_cor:CashAndDeposits>
  <jpdei_cor:CashAndDeposits contextRef="CurrentYearInstant">1200</jpdei_cor:CashAndDeposits>
  <jppfs_cor:NetCashProvidedByUsedInOperatingActivities contextRef="PriorYearDuration">-100</jppfs_cor:NetCashProvidedByUsedInOperatingActivities>
  <jppfs_cor:NetCashProvidedByUsedInOperatingActivities contextRef="CurrentYearDuration">-1200</jppfs_cor:NetCashProvidedByUsedInOperatingActivities>
</xbrli:xbrl>
""",
        encoding="utf-8",
    )

    metrics = extract_cash_metrics_from_xbrl(xbrl_path=xbrl_path)

    assert metrics.cash == 1200.0
    assert metrics.operating_cash_flow == -1200.0

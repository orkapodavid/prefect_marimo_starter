"""XBRL-first cash metric extraction helpers."""

from datetime import date
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from services.financial_monitor.financial_monitor_models import FinancialMonitorCashMetricRecord

XBRL_TAG_CANDIDATES = {
    "cash": ["CashAndDeposits", "CashAndCashEquivalents"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "investing_cash_flow": ["NetCashProvidedByUsedInInvestingActivities"],
    "financing_cash_flow": ["NetCashProvidedByUsedInFinancingActivities"],
}
XBRLI_NAMESPACE = "http://www.xbrl.org/2003/instance"
XBRLDI_NAMESPACE = "http://xbrl.org/2006/xbrldi"


def _parse_context_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _build_context_metadata(root) -> dict[str, dict[str, date | bool | None]]:
    contexts: dict[str, dict[str, date | bool | None]] = {}
    explicit_member_tag = f"{{{XBRLDI_NAMESPACE}}}explicitMember"

    for context in root.iterfind(f".//{{{XBRLI_NAMESPACE}}}context"):
        context_id = context.get("id", "")
        period = context.find(f"{{{XBRLI_NAMESPACE}}}period")
        instant_value = None
        end_date_value = None
        if period is not None:
            instant_value = _parse_context_date(period.findtext(f"{{{XBRLI_NAMESPACE}}}instant"))
            end_date_value = _parse_context_date(period.findtext(f"{{{XBRLI_NAMESPACE}}}endDate"))

        explicit_members = [
            f"{member.get('dimension', '')} {(member.text or '').strip()}".strip()
            for member in context.iterfind(f".//{explicit_member_tag}")
        ]
        contexts[context_id] = {
            "instant": instant_value,
            "end_date": end_date_value,
            "is_non_consolidated": "nonconsolidated" in context_id.lower()
            or any("nonconsolidated" in member.lower() for member in explicit_members),
        }

    return contexts


def _load_xbrl_root(xbrl_path: Path):
    if xbrl_path.suffix.lower() == ".zip":
        with ZipFile(xbrl_path) as archive:
            for name in archive.namelist():
                if name.lower().endswith((".xbrl", ".xml")):
                    with archive.open(name) as handle:
                        return etree.parse(handle).getroot()
        raise ValueError(f"No XBRL instance document found in archive: {xbrl_path}")

    return etree.parse(str(xbrl_path)).getroot()


def _score_context(
    context_ref: str,
    context_metadata: dict[str, dict[str, date | bool | None]],
    *,
    expected_period_type: str,
    period_end: date | None,
) -> tuple[int, int]:
    metadata = context_metadata.get(context_ref, {})
    context_label = context_ref.lower()
    resolved_period_end = metadata.get("end_date") or metadata.get("instant")

    score = 0
    if expected_period_type == "instant":
        score += 40 if metadata.get("instant") else -20
    else:
        score += 40 if metadata.get("end_date") else -20

    if period_end is not None and resolved_period_end is not None:
        score += 80 if resolved_period_end == period_end else -40

    if "current" in context_label:
        score += 30
    if any(marker in context_label for marker in ("prior", "previous", "preceding")):
        score -= 60
    if metadata.get("is_non_consolidated"):
        score -= 50

    recency = resolved_period_end.toordinal() if isinstance(resolved_period_end, date) else 0
    return score, recency


def _extract_numeric_value(
    root,
    candidate_local_names: list[str],
    context_metadata: dict[str, dict[str, date | bool | None]],
    *,
    expected_period_type: str,
    period_end: date | None,
) -> tuple[float | None, str | None]:
    best_match: tuple[tuple[int, int], float, str] | None = None
    for element in root.iter():
        local_name = etree.QName(element.tag).localname
        if local_name not in candidate_local_names:
            continue
        raw_value = (element.text or "").strip().replace(",", "")
        if not raw_value:
            continue
        context_ref = element.get("contextRef", "")
        ranking = _score_context(
            context_ref,
            context_metadata,
            expected_period_type=expected_period_type,
            period_end=period_end,
        )
        prefix = element.prefix or "xbrl"
        candidate_match = (ranking, float(raw_value), f"{prefix}:{local_name}")
        if best_match is None or candidate_match[0] > best_match[0]:
            best_match = candidate_match
    if best_match is None:
        return None, None
    return best_match[1], best_match[2]


def extract_cash_metrics_from_xbrl(
    xbrl_path: Path,
    period_end: date | None = None,
    currency: str = "JPY",
) -> FinancialMonitorCashMetricRecord:
    """Extract cash metrics from an XBRL instance or archive."""
    root = _load_xbrl_root(xbrl_path)
    context_metadata = _build_context_metadata(root)
    extracted_values: dict[str, float | None] = {}
    tag_names: dict[str, str] = {}

    for field_name, candidate_local_names in XBRL_TAG_CANDIDATES.items():
        value, tag_name = _extract_numeric_value(
            root,
            candidate_local_names,
            context_metadata,
            expected_period_type="instant" if field_name == "cash" else "duration",
            period_end=period_end,
        )
        extracted_values[field_name] = value
        if tag_name is not None:
            tag_names[field_name] = tag_name

    return FinancialMonitorCashMetricRecord(
        period_end=period_end,
        currency=currency,
        cash=extracted_values["cash"],
        operating_cash_flow=extracted_values["operating_cash_flow"],
        investing_cash_flow=extracted_values["investing_cash_flow"],
        financing_cash_flow=extracted_values["financing_cash_flow"],
        tag_names=tag_names,
    )

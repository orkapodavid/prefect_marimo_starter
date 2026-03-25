"""EDINET client and normalization helpers for the financial monitor."""

from datetime import date, datetime
import logging
import os
from pathlib import Path
import time

import requests
from dotenv import load_dotenv
from requests import Response
from requests.exceptions import RequestException

from services.financial_monitor.financial_monitor_models import (
    FinancialMonitorEdinetDocument,
    FinancialMonitorTarget,
)
from shared_utils.config import get_settings

EDINET_API_BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"
EDINET_DOCUMENTS_ENDPOINT = f"{EDINET_API_BASE_URL}/documents.json"
EDINET_DOWNLOAD_ENDPOINT = f"{EDINET_API_BASE_URL}/documents"
TDNET_RESULTS_TITLE_MARKERS = ("決算短信", "業績予想", "配当予想")
EDINET_RESULTS_DESCRIPTION_MARKERS = (
    "securities report",
    "quarterly securities report",
    "semiannual securities report",
    "annual securities report",
    "有価証券報告書",
    "四半期報告書",
    "半期報告書",
)
EDINET_CASH_RELEVANT_FORM_CODE_PREFIXES = ("030", "043")

logger = logging.getLogger(__name__)


class FinancialMonitorEdinetError(Exception):
    """Base exception for financial monitor EDINET operations."""


class FinancialMonitorEdinetRequestError(FinancialMonitorEdinetError):
    """Raised when an EDINET HTTP request or API response fails."""


def _parse_submit_datetime(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported EDINET submitDateTime value: {value}")


def _download_url(document_id: str, download_type: int) -> str:
    return f"{EDINET_DOWNLOAD_ENDPOINT}/{document_id}?type={download_type}"


def _raise_for_api_error_payload(payload: dict) -> None:
    raw_status_code = payload.get("statusCode")
    if raw_status_code is None:
        return

    try:
        status_code = int(raw_status_code)
    except (TypeError, ValueError):
        return

    if status_code < 400:
        return

    message = str(payload.get("message") or "Unknown EDINET API error")
    if status_code in (401, 403):
        raise FinancialMonitorEdinetRequestError(
            "EDINET authentication failed. Check EDINET_API_KEY."
        )
    raise FinancialMonitorEdinetRequestError(f"EDINET API error {status_code}: {message}")


def _has_prefect_run_context() -> bool:
    try:
        from prefect.context import get_run_context

        get_run_context()
    except Exception:
        return False
    return True


def resolve_edinet_api_key(settings=None, dotenv_path: Path | None = None) -> str:
    """Resolve the EDINET API key from Prefect first, then the environment."""
    resolved_settings = settings or get_settings()
    if _has_prefect_run_context():
        from prefect.blocks.system import Secret

        try:
            secret_block = Secret.load(
                resolved_settings.financial_monitor_edinet_api_key_block_name
            )
        except ValueError:
            secret_block = None
        except Exception as exc:
            raise ValueError(
                "EDINET API key Prefect Secret block "
                f"`{resolved_settings.financial_monitor_edinet_api_key_block_name}` "
                "could not be resolved."
            ) from exc

        if secret_block is not None:
            try:
                secret_value = secret_block.get()
            except Exception as exc:
                raise ValueError(
                    "EDINET API key Prefect Secret block "
                    f"`{resolved_settings.financial_monitor_edinet_api_key_block_name}` "
                    "could not be resolved."
                ) from exc
            if secret_value:
                return secret_value
    else:
        resolved_dotenv_path = dotenv_path or Path(__file__).resolve().parents[3] / ".env"
        load_dotenv(dotenv_path=resolved_dotenv_path, override=False)

    env_value = os.getenv("EDINET_API_KEY", "").strip()
    if env_value:
        return env_value

    raise ValueError(
        "EDINET API key is not configured. Set the Prefect Secret block "
        "`financial-monitor-edinet-api-key` or the `EDINET_API_KEY` environment variable."
    )


def normalize_edinet_documents(payload: dict) -> list[FinancialMonitorEdinetDocument]:
    """Normalize EDINET API response payloads into typed document records."""
    _raise_for_api_error_payload(payload)
    normalized_documents: list[FinancialMonitorEdinetDocument] = []
    for item in payload.get("results", []):
        document_id = item.get("docID", "")
        has_xbrl = str(item.get("xbrlFlag", "")) == "1"
        has_pdf = str(item.get("pdfFlag", "")) == "1"
        has_csv = str(item.get("csvFlag", "")) == "1"
        normalized_documents.append(
            FinancialMonitorEdinetDocument(
                document_id=document_id,
                edinet_code=item.get("edinetCode", ""),
                filer_name=item.get("filerName", ""),
                securities_code=item.get("secCode"),
                description=item.get("docDescription", ""),
                form_code=item.get("formCode"),
                filed_at=_parse_submit_datetime(item.get("submitDateTime", "")),
                has_xbrl=has_xbrl,
                has_pdf=has_pdf,
                has_csv=has_csv,
                xbrl_download_url=(
                    _download_url(document_id, 1) if has_xbrl else None
                ),
                pdf_download_url=(
                    _download_url(document_id, 2) if has_pdf else None
                ),
                csv_download_url=(_download_url(document_id, 5) if has_csv else None),
                raw=dict(item),
            )
        )
    return normalized_documents


def _is_results_like_tdnet_candidate(candidate: dict) -> bool:
    title = str(candidate.get("title", ""))
    return bool(candidate.get("has_xbrl")) or any(
        marker in title for marker in TDNET_RESULTS_TITLE_MARKERS
    )


def _is_cash_relevant_edinet_document(document: FinancialMonitorEdinetDocument) -> bool:
    if not document.has_xbrl:
        return False

    form_code = str(document.form_code or "").strip()
    if any(form_code.startswith(prefix) for prefix in EDINET_CASH_RELEVANT_FORM_CODE_PREFIXES):
        return True

    description = str(document.description or "").lower()
    return any(marker in description for marker in EDINET_RESULTS_DESCRIPTION_MARKERS)


def select_tdnet_scoped_edinet_documents(
    *,
    documents: list[FinancialMonitorEdinetDocument],
    tdnet_candidates: list[dict],
    targets: list[FinancialMonitorTarget],
) -> list[FinancialMonitorEdinetDocument]:
    """Keep only EDINET documents that are in-scope for TDnet-matched targets."""
    targets_by_id = {target.id: target for target in targets}
    matched_tdnet_edinet_codes = {
        candidate.get("edinet_code", "")
        for candidate in tdnet_candidates
        if candidate.get("edinet_code")
        and _is_results_like_tdnet_candidate(candidate)
        and (target := targets_by_id.get(candidate.get("target_id")))
        and target.enabled
        and target.include_edinet
    }
    if not matched_tdnet_edinet_codes:
        return []

    return [
        document
        for document in documents
        if document.edinet_code in matched_tdnet_edinet_codes
        and _is_cash_relevant_edinet_document(document)
    ]


class FinancialMonitorEdinetClient:
    """Thin EDINET API client for document discovery."""

    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_delays: tuple[float, ...] = (1.0, 2.0, 4.0),
        rate_limit_backoff_delays: tuple[float, ...] = (2.0, 4.0, 8.0),
        session: requests.Session | None = None,
    ):
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_delays = retry_backoff_delays
        self.rate_limit_backoff_delays = rate_limit_backoff_delays
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "prefect-marimo-financial-monitor/1.0",
            }
        )

    def _get_retry_delay(self, attempt: int) -> float:
        return self.retry_backoff_delays[min(attempt, len(self.retry_backoff_delays) - 1)]

    def _get_rate_limit_delay(self, attempt: int) -> float:
        return self.rate_limit_backoff_delays[
            min(attempt, len(self.rate_limit_backoff_delays) - 1)
        ]

    def _request(self, method: str, url: str, *, params: dict | None = None) -> Response:
        request_params = dict(params or {})
        request_params.setdefault("Subscription-Key", self.api_key)
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method,
                    url,
                    params=request_params,
                    timeout=self.timeout,
                )
                if response.status_code == 429 and attempt < self.max_retries - 1:
                    delay = self._get_rate_limit_delay(attempt)
                    logger.warning(
                        "Retrying EDINET request after status 429 with %.1fs backoff",
                        delay,
                    )
                    time.sleep(delay)
                    continue
                if response.status_code in (401, 403):
                    raise FinancialMonitorEdinetRequestError(
                        "EDINET authentication failed. Check EDINET_API_KEY."
                    )
                if 500 <= response.status_code < 600 and attempt < self.max_retries - 1:
                    delay = self._get_retry_delay(attempt)
                    logger.warning(
                        "Retrying EDINET request after status %s with %.1fs backoff",
                        response.status_code,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                response.raise_for_status()
                return response
            except RequestException as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    delay = self._get_retry_delay(attempt)
                    logger.warning(
                        "Retrying EDINET request after transport error with %.1fs backoff",
                        delay,
                    )
                    time.sleep(delay)
                    continue
                break

        raise FinancialMonitorEdinetRequestError(f"EDINET request failed for {url}: {last_error}")

    def list_documents_by_date(self, filing_date: date) -> list[FinancialMonitorEdinetDocument]:
        """List EDINET documents for a filing date."""
        response = self._request(
            "GET",
            EDINET_DOCUMENTS_ENDPOINT,
            params={"date": filing_date.isoformat(), "type": 2},
        )
        return normalize_edinet_documents(response.json())

    def download_document(self, document_id: str, *, kind: str = "zip") -> bytes:
        """Download an EDINET document payload."""
        type_by_kind = {"zip": 1, "pdf": 2, "csv": 5}
        try:
            download_type = type_by_kind[kind]
        except KeyError as exc:
            raise ValueError(f"Unsupported EDINET download kind: {kind}") from exc

        response = self._request(
            "GET",
            f"{EDINET_DOWNLOAD_ENDPOINT}/{document_id}",
            params={"type": download_type},
        )
        if "json" in response.headers.get("Content-Type", "").lower():
            _raise_for_api_error_payload(response.json())
        return response.content

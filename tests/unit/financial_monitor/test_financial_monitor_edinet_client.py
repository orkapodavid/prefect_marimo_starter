import json
from datetime import datetime
from pathlib import Path

import pytest

from services.financial_monitor.financial_monitor_document_store import write_source_document
from services.financial_monitor.financial_monitor_edinet_client import (
    EDINET_API_BASE_URL,
    FinancialMonitorEdinetClient,
    FinancialMonitorEdinetRequestError,
    select_tdnet_scoped_edinet_documents,
    normalize_edinet_documents,
    resolve_edinet_api_key,
)
from services.financial_monitor.financial_monitor_models import (
    FinancialMonitorEdinetDocument,
    FinancialMonitorTarget,
)


class _SettingsStub:
    financial_monitor_edinet_api_key_block_name = "financial-monitor-edinet-api-key"


def test_edinet_client_uses_json_api_host():
    assert EDINET_API_BASE_URL == "https://api.edinet-fsa.go.jp/api/v2"


def test_resolve_edinet_api_key_prefers_prefect_block_then_env(monkeypatch):
    class _Block:
        def get(self) -> str:
            return "block-key"

    from prefect.blocks.system import Secret

    monkeypatch.setattr(
        "services.financial_monitor.financial_monitor_edinet_client._has_prefect_run_context",
        lambda: True,
    )
    monkeypatch.setattr(Secret, "load", classmethod(lambda cls, name: _Block()))
    monkeypatch.setenv("EDINET_API_KEY", "env-key")

    assert resolve_edinet_api_key(settings=_SettingsStub()) == "block-key"


def test_resolve_edinet_api_key_falls_back_to_env(monkeypatch):
    from prefect.blocks.system import Secret

    def raise_missing_block(cls, name):
        raise ValueError("missing block")

    monkeypatch.setattr(
        "services.financial_monitor.financial_monitor_edinet_client._has_prefect_run_context",
        lambda: True,
    )
    monkeypatch.setattr(Secret, "load", classmethod(raise_missing_block))
    monkeypatch.setenv("EDINET_API_KEY", "env-key")

    assert resolve_edinet_api_key(settings=_SettingsStub()) == "env-key"


def test_resolve_edinet_api_key_loads_repo_dotenv(monkeypatch, tmp_path: Path):
    from prefect.blocks.system import Secret

    def raise_missing_block(cls, name):
        raise ValueError("missing block")

    monkeypatch.setattr(Secret, "load", classmethod(raise_missing_block))
    monkeypatch.delenv("EDINET_API_KEY", raising=False)
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("EDINET_API_KEY=dotenv-key\n", encoding="utf-8")

    assert resolve_edinet_api_key(
        settings=_SettingsStub(),
        dotenv_path=dotenv_path,
    ) == "dotenv-key"


def test_resolve_edinet_api_key_does_not_load_repo_dotenv_in_prefect_context(
    monkeypatch,
    tmp_path: Path,
):
    from prefect.blocks.system import Secret

    def raise_missing_block(cls, name):
        raise ValueError("missing block")

    monkeypatch.setattr(
        "services.financial_monitor.financial_monitor_edinet_client._has_prefect_run_context",
        lambda: True,
    )
    monkeypatch.setattr(Secret, "load", classmethod(raise_missing_block))
    monkeypatch.delenv("EDINET_API_KEY", raising=False)
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("EDINET_API_KEY=dotenv-key\n", encoding="utf-8")

    with pytest.raises(ValueError, match="EDINET API key is not configured"):
        resolve_edinet_api_key(
            settings=_SettingsStub(),
            dotenv_path=dotenv_path,
        )


def test_resolve_edinet_api_key_raises_when_prefect_secret_block_read_fails(monkeypatch):
    class _BrokenBlock:
        def get(self) -> str:
            raise RuntimeError("prefect api unavailable")

    from prefect.blocks.system import Secret

    monkeypatch.setattr(
        "services.financial_monitor.financial_monitor_edinet_client._has_prefect_run_context",
        lambda: True,
    )
    monkeypatch.setattr(Secret, "load", classmethod(lambda cls, name: _BrokenBlock()))
    monkeypatch.setenv("EDINET_API_KEY", "env-key")

    with pytest.raises(ValueError, match="Prefect Secret block"):
        resolve_edinet_api_key(settings=_SettingsStub())


def test_normalize_edinet_documents_returns_typed_records(
    financial_monitor_fixtures_dir: Path,
):
    payload = json.loads(
        (financial_monitor_fixtures_dir / "edinet/edinet_documents.json").read_text(
            encoding="utf-8"
        )
    )

    documents = normalize_edinet_documents(payload)

    assert len(documents) == 1
    assert documents[0].document_id == "S100TEST"
    assert documents[0].edinet_code == "E02529"
    assert documents[0].securities_code == "80580"
    assert documents[0].form_code == "043000"
    assert documents[0].has_xbrl is True
    assert documents[0].has_csv is True
    assert documents[0].xbrl_download_url.endswith("/S100TEST?type=1")
    assert documents[0].csv_download_url.endswith("/S100TEST?type=5")


def test_normalize_edinet_documents_raises_for_api_error_payload():
    payload = {"statusCode": 401, "message": "invalid subscription key"}

    with pytest.raises(
        FinancialMonitorEdinetRequestError,
        match="EDINET authentication failed",
    ):
        normalize_edinet_documents(payload)


def test_normalize_edinet_documents_coerces_null_text_fields_to_empty_strings():
    payload = {
        "results": [
            {
                "docID": "S100XSZS",
                "edinetCode": None,
                "filerName": None,
                "docDescription": None,
                "submitDateTime": "2026-03-24 09:41",
                "xbrlFlag": "0",
                "pdfFlag": "1",
            }
        ]
    }

    documents = normalize_edinet_documents(payload)

    assert len(documents) == 1
    assert documents[0].document_id == "S100XSZS"
    assert documents[0].edinet_code == ""
    assert documents[0].filer_name == ""
    assert documents[0].description == ""


def test_select_tdnet_scoped_edinet_documents_filters_to_results_like_targets():
    targets = [
        FinancialMonitorTarget(
            id="results_target",
            company_id="mitsubishi",
            company_name="Mitsubishi Corporation",
            ticker="8058.T",
            exchange="TSE",
            edinet_code="E02529",
            tdnet_language="japanese",
            disclosure_keywords=["決算短信"],
            include_edinet=True,
            enabled=True,
        ),
        FinancialMonitorTarget(
            id="borrowing_target",
            company_id="sumitomo",
            company_name="Sumitomo Corporation",
            ticker="8053.T",
            exchange="TSE",
            edinet_code="E02530",
            tdnet_language="japanese",
            disclosure_keywords=["資金の借入"],
            include_edinet=True,
            enabled=True,
        ),
    ]
    documents = [
        FinancialMonitorEdinetDocument(
            document_id="S100RESULT",
            edinet_code="E02529",
            filer_name="Mitsubishi Corporation",
            description="Quarterly Securities Report",
            form_code="043000",
            filed_at=datetime(2026, 3, 25, 15, 0, 0),
            has_xbrl=True,
            xbrl_download_url="https://edinet.example/S100RESULT?type=1",
        ),
        FinancialMonitorEdinetDocument(
            document_id="S100UNRELATED",
            edinet_code="E02529",
            filer_name="Mitsubishi Corporation",
            description="Internal Control Report",
            form_code="060000",
            filed_at=datetime(2026, 3, 25, 16, 0, 0),
            has_xbrl=True,
            xbrl_download_url="https://edinet.example/S100UNRELATED?type=1",
        ),
        FinancialMonitorEdinetDocument(
            document_id="S100BORROW",
            edinet_code="E02530",
            filer_name="Sumitomo Corporation",
            description="Quarterly Securities Report",
            form_code="043000",
            filed_at=datetime(2026, 3, 25, 17, 0, 0),
            has_xbrl=True,
            xbrl_download_url="https://edinet.example/S100BORROW?type=1",
        ),
    ]

    selected_documents = select_tdnet_scoped_edinet_documents(
        documents=documents,
        tdnet_candidates=[
            {
                "target_id": "results_target",
                "title": "2026年3月期 第3四半期決算短信〔IFRS〕（連結）",
                "edinet_code": "E02529",
                "has_xbrl": True,
            },
            {
                "target_id": "borrowing_target",
                "title": "資金の借入に関するお知らせ",
                "edinet_code": "E02530",
                "has_xbrl": False,
            },
        ],
        targets=targets,
    )

    assert [document.document_id for document in selected_documents] == ["S100RESULT"]


def test_select_tdnet_scoped_edinet_documents_respects_include_edinet_and_japanese_form_codes():
    targets = [
        FinancialMonitorTarget(
            id="max_results_target",
            company_id="max",
            company_name="Max Co., Ltd.",
            ticker="6454.T",
            exchange="TSE",
            edinet_code="E02381",
            tdnet_language="japanese",
            disclosure_keywords=["決算短信"],
            include_edinet=True,
            enabled=True,
        ),
        FinancialMonitorTarget(
            id="disabled_edinet_target",
            company_id="mitsubishi",
            company_name="Mitsubishi Corporation",
            ticker="8058.T",
            exchange="TSE",
            edinet_code="E02529",
            tdnet_language="japanese",
            disclosure_keywords=["決算短信"],
            include_edinet=False,
            enabled=True,
        ),
    ]
    documents = [
        FinancialMonitorEdinetDocument(
            document_id="S100XTLI",
            edinet_code="E02381",
            filer_name="マックス株式会社",
            description="訂正半期報告書－第95期(2025/04/01－2026/03/31)",
            form_code="043A01",
            filed_at=datetime(2026, 3, 25, 15, 0, 0),
            has_xbrl=True,
            xbrl_download_url="https://edinet.example/S100XTLI?type=1",
        ),
        FinancialMonitorEdinetDocument(
            document_id="S100OPTEDOUT",
            edinet_code="E02529",
            filer_name="Mitsubishi Corporation",
            description="Quarterly Securities Report",
            form_code="043000",
            filed_at=datetime(2026, 3, 25, 16, 0, 0),
            has_xbrl=True,
            xbrl_download_url="https://edinet.example/S100OPTEDOUT?type=1",
        ),
    ]

    selected_documents = select_tdnet_scoped_edinet_documents(
        documents=documents,
        tdnet_candidates=[
            {
                "target_id": "max_results_target",
                "title": "（訂正・数値データ訂正）「2026年3月期 第2四半期（中間期）決算短信〔日本基準〕（連結）」の一部訂正について",
                "edinet_code": "E02381",
                "has_xbrl": True,
            },
            {
                "target_id": "disabled_edinet_target",
                "title": "2026年3月期 第3四半期決算短信〔IFRS〕（連結）",
                "edinet_code": "E02529",
                "has_xbrl": True,
            },
        ],
        targets=targets,
    )

    assert [document.document_id for document in selected_documents] == ["S100XTLI"]


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.headers = {"Content-Type": "application/json"}
        self.content = json.dumps(payload).encode("utf-8")

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]):
        self._responses = responses
        self.calls = 0
        self.headers: dict[str, str] = {}

    def request(self, method: str, url: str, params: dict, timeout: int):
        response = self._responses[self.calls]
        self.calls += 1
        return response


def test_list_documents_by_date_retries_after_429():
    session = _FakeSession(
        responses=[
            _FakeResponse(status_code=429, payload={"message": "rate limited"}),
            _FakeResponse(
                status_code=200,
                payload={
                    "metadata": {"resultSetCount": 1},
                    "results": [
                        {
                            "docID": "S100TEST",
                            "edinetCode": "E02529",
                            "filerName": "Mitsubishi Corporation",
                            "docDescription": "Quarterly Securities Report",
                            "submitDateTime": "2026-03-25 15:00",
                            "xbrlFlag": "1",
                            "pdfFlag": "1",
                        }
                    ],
                },
            ),
        ]
    )
    client = FinancialMonitorEdinetClient(
        api_key="test-key",
        session=session,
        max_retries=2,
        retry_backoff_delays=(0.0, 0.0),
        rate_limit_backoff_delays=(0.0, 0.0),
    )

    documents = client.list_documents_by_date(filing_date=__import__("datetime").date(2026, 3, 25))

    assert session.calls == 2
    assert len(documents) == 1
    assert documents[0].document_id == "S100TEST"


def test_write_source_document_uses_deterministic_raw_relative_paths(tmp_path: Path):
    workspace_dir = tmp_path / "data/financial_monitor/prod"

    written_path = write_source_document(
        workspace_dir=workspace_dir,
        source="edinet",
        document_id="S100TEST",
        filename="report.zip",
        content=b"payload",
    )

    assert written_path.relative_to(workspace_dir) == Path("raw/edinet/S100TEST/report.zip")
    assert written_path.read_bytes() == b"payload"
    assert (workspace_dir / "raw/tdnet").is_dir()
    assert (workspace_dir / "raw/edinet").is_dir()
    assert (workspace_dir / "manifests").is_dir()

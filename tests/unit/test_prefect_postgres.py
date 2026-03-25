import pytest

from shared_utils.prefect_postgres import (
    build_connect_kwargs_from_connection_url,
    parse_search_path_schema,
)


def test_parse_search_path_schema_returns_first_schema_and_requires_public():
    schema = parse_search_path_schema("prefect_marimo_starter,public")

    assert schema == "prefect_marimo_starter"


def test_parse_search_path_schema_rejects_missing_public():
    with pytest.raises(ValueError, match="public"):
        parse_search_path_schema("prefect_marimo_starter")


def test_parse_search_path_schema_rejects_invalid_identifier():
    with pytest.raises(ValueError, match="Invalid PostgreSQL schema"):
        parse_search_path_schema("prefect-marimo-starter,public")


def test_build_connect_kwargs_from_connection_url_parses_asyncpg_url():
    kwargs = build_connect_kwargs_from_connection_url(
        "postgresql+asyncpg://prefect:secret@host.docker.internal:5432/workflow_app"
    )

    assert kwargs == {
        "database": "workflow_app",
        "host": "host.docker.internal",
        "password": "secret",
        "port": 5432,
        "user": "prefect",
    }


def test_build_connect_kwargs_from_connection_url_rejects_non_postgres_urls():
    with pytest.raises(ValueError, match="PostgreSQL"):
        build_connect_kwargs_from_connection_url("sqlite+aiosqlite:///tmp/prefect.db")

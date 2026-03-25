from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Mapping

import asyncpg
from sqlalchemy.engine import make_url


_POSTGRES_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parse_search_path_schema(search_path: str) -> str:
    parts = [part.strip() for part in search_path.split(",") if part.strip()]
    if not parts:
        raise ValueError("Prefect PostgreSQL search_path must contain at least one schema")
    if "public" not in parts:
        raise ValueError("Prefect PostgreSQL search_path must include public")

    schema = parts[0]
    if not _POSTGRES_IDENTIFIER.fullmatch(schema):
        raise ValueError(f"Invalid PostgreSQL schema identifier: {schema}")
    return schema


def build_connect_kwargs_from_connection_url(connection_url: str) -> dict[str, object]:
    url = make_url(connection_url)
    if not url.drivername.startswith("postgresql"):
        raise ValueError("Prefect PostgreSQL bootstrap requires a PostgreSQL connection URL")
    if url.get_backend_name() != "postgresql":
        raise ValueError("Prefect PostgreSQL bootstrap requires a PostgreSQL connection URL")
    if not url.host or not url.database or not url.username:
        raise ValueError(
            "Prefect PostgreSQL connection URL must include host, database, and user"
        )

    return {
        "database": url.database,
        "host": url.host,
        "password": url.password,
        "port": url.port or 5432,
        "user": url.username,
    }


async def ensure_prefect_schema_exists(env: Mapping[str, str] | None = None) -> str:
    runtime_env = env or os.environ
    connection_url = runtime_env.get("PREFECT_API_DATABASE_CONNECTION_URL") or runtime_env.get(
        "PREFECT_SERVER_DATABASE_CONNECTION_URL"
    )
    if not connection_url:
        raise RuntimeError("Prefect PostgreSQL bootstrap requires PREFECT_API_DATABASE_CONNECTION_URL")

    search_path = runtime_env.get(
        "PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH"
    ) or runtime_env.get("PREFECT_API_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH")
    if not search_path:
        raise RuntimeError(
            "Prefect PostgreSQL bootstrap requires "
            "PREFECT_SERVER_DATABASE_SQLALCHEMY_CONNECT_ARGS_SEARCH_PATH"
        )

    schema = parse_search_path_schema(search_path)
    connect_kwargs = build_connect_kwargs_from_connection_url(connection_url)

    connection = await asyncpg.connect(**connect_kwargs)
    try:
        await connection.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public")
        await connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    finally:
        await connection.close()
    return schema


def main() -> None:
    schema = asyncio.run(ensure_prefect_schema_exists())
    print(f"Ensured Prefect PostgreSQL schema '{schema}' exists", flush=True)


if __name__ == "__main__":
    main()

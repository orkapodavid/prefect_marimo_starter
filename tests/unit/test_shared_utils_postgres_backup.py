from __future__ import annotations

import hashlib
import importlib
import os
from datetime import datetime, timedelta

import pytest


def load_backup_utils():
    try:
        return importlib.import_module("src.shared_utils.shared_utils_postgres_backup")
    except ModuleNotFoundError as exc:
        pytest.fail(f"PostgreSQL backup helper module is missing: {exc}")


def test_build_backup_artifacts_uses_database_and_timestamp(tmp_path):
    backup_utils = load_backup_utils()
    now = datetime(2026, 3, 23, 2, 0, 0)

    artifacts = backup_utils.build_backup_artifacts(
        backup_dir=tmp_path,
        database="workflow_app",
        now=now,
    )

    assert artifacts.dump_file == tmp_path / "workflow_app_20260323_020000.dump"
    assert artifacts.checksum_file == tmp_path / "workflow_app_20260323_020000.dump.sha256"


def test_build_postgres_commands_use_explicit_args(tmp_path):
    backup_utils = load_backup_utils()
    dump_file = tmp_path / "workflow_app_20260323_020000.dump"

    pg_isready_command = backup_utils.build_pg_isready_command(
        host="localhost",
        port=5432,
        user="backup_user",
        database="workflow_app",
        timeout_seconds=15,
    )
    pg_dump_command = backup_utils.build_pg_dump_command(
        host="localhost",
        port=5432,
        user="backup_user",
        database="workflow_app",
        dump_file=dump_file,
        compression_level=6,
        timeout_seconds=15,
    )
    pg_restore_command = backup_utils.build_pg_restore_list_command(dump_file)

    assert pg_isready_command == [
        "pg_isready",
        "-h",
        "localhost",
        "-p",
        "5432",
        "-U",
        "backup_user",
        "-d",
        "workflow_app",
        "-t",
        "15",
    ]
    assert pg_dump_command == [
        "pg_dump",
        "-h",
        "localhost",
        "-p",
        "5432",
        "-U",
        "backup_user",
        "-F",
        "c",
        "-Z",
        "6",
        "-v",
        "-f",
        str(dump_file),
        "workflow_app",
    ]
    assert pg_restore_command == ["pg_restore", "-l", str(dump_file)]


def test_calculate_sha256_returns_expected_digest(tmp_path):
    backup_utils = load_backup_utils()
    dump_file = tmp_path / "workflow_app_20260323_020000.dump"
    dump_file.write_bytes(b"postgres-backup-payload")

    digest = backup_utils.calculate_sha256(dump_file)

    assert digest == hashlib.sha256(b"postgres-backup-payload").hexdigest()


def test_find_backup_files_to_prune_returns_expired_dump_and_checksum(tmp_path):
    backup_utils = load_backup_utils()
    now = datetime(2026, 3, 23, 9, 0, 0)

    stale_dump = tmp_path / "workflow_app_20260101_020000.dump"
    stale_checksum = tmp_path / "workflow_app_20260101_020000.dump.sha256"
    fresh_dump = tmp_path / "workflow_app_20260322_020000.dump"
    fresh_checksum = tmp_path / "workflow_app_20260322_020000.dump.sha256"

    for file_path in [stale_dump, stale_checksum, fresh_dump, fresh_checksum]:
        file_path.write_text(file_path.name, encoding="utf-8")

    stale_ts = (now - timedelta(days=60)).timestamp()
    fresh_ts = (now - timedelta(days=1)).timestamp()
    os.utime(stale_dump, (stale_ts, stale_ts))
    os.utime(stale_checksum, (stale_ts, stale_ts))
    os.utime(fresh_dump, (fresh_ts, fresh_ts))
    os.utime(fresh_checksum, (fresh_ts, fresh_ts))

    candidates = backup_utils.find_backup_files_to_prune(
        backup_dir=tmp_path,
        retention_days=30,
        now=now,
    )

    assert candidates == [stale_dump, stale_checksum]

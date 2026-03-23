from __future__ import annotations

import importlib
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def load_config_module():
    return importlib.import_module("src.shared_utils.config")


def load_maintenance_module():
    try:
        return importlib.import_module("notebooks.maintenance.maintenance_pg_backup")
    except ModuleNotFoundError as exc:
        pytest.fail(f"PostgreSQL maintenance notebook module is missing: {exc}")


def test_resolve_pg_backup_password_prefers_secret_block(monkeypatch):
    config = load_config_module()
    config.get_settings.cache_clear()
    monkeypatch.setenv("PG_BACKUP_PASSWORD", "env-password")

    settings = config.Settings(
        pg_backup_password="settings-password",
        pg_backup_password_block_name="pg-backup-password",
    )

    secret_block = MagicMock()
    secret_block.get.return_value = "secret-block-password"

    with patch("prefect.blocks.system.Secret.load", return_value=secret_block) as mock_load:
        resolved_password = config.resolve_pg_backup_password(settings)

    assert resolved_password == "secret-block-password"
    mock_load.assert_called_once_with("pg-backup-password")


def test_resolve_pg_backup_password_uses_env_when_secret_block_is_not_configured(monkeypatch):
    config = load_config_module()
    config.get_settings.cache_clear()
    monkeypatch.setenv("PG_BACKUP_PASSWORD", "env-password")

    settings = config.Settings(
        pg_backup_password="",
        pg_backup_password_block_name=None,
    )

    assert config.resolve_pg_backup_password(settings) == "env-password"


def test_resolve_pg_backup_password_raises_when_missing(monkeypatch):
    config = load_config_module()
    config.get_settings.cache_clear()
    monkeypatch.delenv("PG_BACKUP_PASSWORD", raising=False)

    settings = config.Settings(
        pg_backup_password="",
        pg_backup_password_block_name=None,
    )

    with pytest.raises(ValueError, match="PG_BACKUP_PASSWORD"):
        config.resolve_pg_backup_password(settings)


def test_check_backup_prerequisites_raises_when_required_binary_is_missing(monkeypatch):
    module = load_maintenance_module()
    backup_dir = Path("D:/Backups/postgres")

    config = {
        "database": "workflow_app",
        "backup_dir": backup_dir,
        "min_free_space_bytes": 5 * 1024**3,
    }

    monkeypatch.setattr(module.shutil, "which", lambda binary: None if binary == "pg_restore" else f"/usr/bin/{binary}")
    monkeypatch.setattr(module.shutil, "disk_usage", lambda path: SimpleNamespace(total=100, used=20, free=80))
    monkeypatch.setattr(Path, "mkdir", lambda self, parents=False, exist_ok=False: None, raising=False)

    with pytest.raises(FileNotFoundError, match="pg_restore"):
        module.check_backup_prerequisites.fn(config)


def test_check_backup_prerequisites_raises_when_free_space_is_too_low(monkeypatch):
    module = load_maintenance_module()
    backup_dir = Path("D:/Backups/postgres")
    prior_dump = backup_dir / "workflow_app_20260322_020000.dump"

    config = {
        "database": "workflow_app",
        "backup_dir": backup_dir,
        "min_free_space_bytes": 5 * 1024**3,
    }

    monkeypatch.setattr(module.shutil, "which", lambda binary: f"/usr/bin/{binary}")
    monkeypatch.setattr(
        module.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(total=100 * 1024**3, used=97 * 1024**3, free=3 * 1024**3),
    )
    monkeypatch.setattr(Path, "mkdir", lambda self, parents=False, exist_ok=False: None, raising=False)
    monkeypatch.setattr(
        Path,
        "iterdir",
        lambda self: iter([prior_dump]) if self == backup_dir else iter(()),
        raising=False,
    )

    def fake_stat(self):
        if self == prior_dump:
            return SimpleNamespace(st_size=4 * 1024**3, st_mtime=datetime(2026, 3, 22, 2, 0, 0).timestamp())
        raise FileNotFoundError(self)

    monkeypatch.setattr(Path, "stat", fake_stat, raising=False)

    with pytest.raises(RuntimeError, match="free disk space"):
        module.check_backup_prerequisites.fn(config)


def test_check_pg_connection_raises_on_subprocess_failure(monkeypatch):
    module = load_maintenance_module()

    config = {
        "host": "localhost",
        "port": 5432,
        "user": "backup_user",
        "database": "workflow_app",
        "connect_timeout_seconds": 15,
        "password": "super-secret",
    }

    failed_process = SimpleNamespace(returncode=1, stdout="", stderr="connection failed")
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: failed_process)

    with pytest.raises(RuntimeError, match="connection failed"):
        module.check_pg_connection.fn(config)


def test_run_pg_dump_raises_on_subprocess_failure(monkeypatch):
    module = load_maintenance_module()
    dump_file = Path("D:/Backups/postgres/workflow_app_20260323_020000.dump")

    config = {
        "host": "localhost",
        "port": 5432,
        "user": "backup_user",
        "database": "workflow_app",
        "compression_level": 6,
        "connect_timeout_seconds": 15,
        "timeout_seconds": 3600,
        "password": "super-secret",
        "artifacts": {
            "dump_file": dump_file,
            "checksum_file": Path(f"{dump_file}.sha256"),
        },
    }

    failed_process = SimpleNamespace(returncode=1, stdout="", stderr="pg_dump failed")
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: failed_process)

    with pytest.raises(RuntimeError, match="pg_dump failed"):
        module.run_pg_dump.fn(config)


def test_prune_old_backups_unlinks_expired_artifacts(monkeypatch):
    module = load_maintenance_module()
    stale_dump = Path("D:/Backups/postgres/workflow_app_20260101_020000.dump")
    stale_checksum = Path(f"{stale_dump}.sha256")

    config = {
        "backup_dir": Path("D:/Backups/postgres"),
        "retention_days": 30,
    }

    deleted_paths: list[Path] = []

    monkeypatch.setattr(module, "find_backup_files_to_prune", lambda **kwargs: [stale_dump, stale_checksum])
    monkeypatch.setattr(
        Path,
        "unlink",
        lambda self, missing_ok=False: deleted_paths.append(self),
        raising=False,
    )

    result = module.prune_old_backups.fn(config, dry_run=False)

    assert result == {
        "pruned_files": [str(stale_dump), str(stale_checksum)],
        "pruned_file_count": 2,
    }
    assert deleted_paths == [stale_dump, stale_checksum]


def test_build_backup_summary_returns_expected_shape():
    module = load_maintenance_module()
    started_at = datetime(2026, 3, 23, 2, 0, 0)
    completed_at = datetime(2026, 3, 23, 2, 15, 0)

    config = {
        "database": "workflow_app",
        "backup_dir": Path("D:/Backups/postgres"),
    }
    dump_result = {
        "dump_file": "D:/Backups/postgres/workflow_app_20260323_020000.dump",
        "size_bytes": 4096,
    }
    verify_result = {
        "verified": True,
    }
    checksum_result = {
        "checksum_file": "D:/Backups/postgres/workflow_app_20260323_020000.dump.sha256",
        "sha256": "abc123",
    }
    prune_result = {
        "pruned_files": ["D:/Backups/postgres/workflow_app_20260101_020000.dump"],
        "pruned_file_count": 1,
    }

    summary = module.build_backup_summary.fn(
        config,
        dump_result,
        verify_result,
        checksum_result,
        prune_result,
        started_at,
        completed_at,
        False,
    )

    assert summary == {
        "database": "workflow_app",
        "backup_dir": "D:/Backups/postgres",
        "dump_file": "D:/Backups/postgres/workflow_app_20260323_020000.dump",
        "dump_size_bytes": 4096,
        "checksum_file": "D:/Backups/postgres/workflow_app_20260323_020000.dump.sha256",
        "sha256": "abc123",
        "verified": True,
        "pruned_files": ["D:/Backups/postgres/workflow_app_20260101_020000.dump"],
        "pruned_file_count": 1,
        "dry_run": False,
        "started_at": "2026-03-23T02:00:00",
        "completed_at": "2026-03-23T02:15:00",
    }


def test_run_pg_backup_flow_returns_summary(monkeypatch):
    module = load_maintenance_module()
    expected_summary = {
        "database": "workflow_app",
        "dump_file": "D:/Backups/postgres/workflow_app_20260323_020000.dump",
        "verified": True,
    }

    monkeypatch.setattr(
        module,
        "resolve_backup_config",
        lambda **kwargs: {
            "database": "workflow_app",
            "backup_dir": Path("D:/Backups/postgres"),
            "retention_days": 30,
            "compression_level": 6,
            "artifacts": {
                "dump_file": Path("D:/Backups/postgres/workflow_app_20260323_020000.dump"),
                "checksum_file": Path("D:/Backups/postgres/workflow_app_20260323_020000.dump.sha256"),
            },
        },
    )
    monkeypatch.setattr(module, "check_backup_prerequisites", lambda config: {"free_bytes": 8 * 1024**3})
    monkeypatch.setattr(module, "check_pg_connection", lambda config: {"reachable": True})
    monkeypatch.setattr(
        module,
        "run_pg_dump",
        lambda config: {
            "dump_file": "D:/Backups/postgres/workflow_app_20260323_020000.dump",
            "size_bytes": 4096,
        },
    )
    monkeypatch.setattr(module, "verify_dump", lambda config, dump_result, verify_restore=True, dry_run=False: {"verified": True})
    monkeypatch.setattr(
        module,
        "write_checksum",
        lambda config, dump_result, dry_run=False: {
            "checksum_file": "D:/Backups/postgres/workflow_app_20260323_020000.dump.sha256",
            "sha256": "abc123",
        },
    )
    monkeypatch.setattr(module, "prune_old_backups", lambda config, dry_run=False: {"pruned_files": [], "pruned_file_count": 0})
    monkeypatch.setattr(module, "build_backup_summary", lambda *args, **kwargs: expected_summary)

    result = module.run_pg_backup.fn(
        database="workflow_app",
        backup_dir="D:/Backups/postgres",
        retention_days=30,
        compression_level=6,
        verify_restore=True,
        dry_run=False,
    )

    assert result == expected_summary

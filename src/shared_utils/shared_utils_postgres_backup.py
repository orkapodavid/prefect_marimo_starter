"""Pure helpers for PostgreSQL backup workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
from pathlib import Path


@dataclass(frozen=True)
class PgBackupArtifacts:
    """Paths for a PostgreSQL dump and its checksum sidecar."""

    dump_file: Path
    checksum_file: Path


def build_dump_filename(database: str, now: datetime) -> str:
    """Build a timestamped dump filename."""
    return f"{database}_{now:%Y%m%d_%H%M%S}.dump"


def build_checksum_file_path(dump_file: Path) -> Path:
    """Build the checksum sidecar path for a dump file."""
    return dump_file.with_name(f"{dump_file.name}.sha256")


def build_backup_artifacts(backup_dir: Path, database: str, now: datetime) -> PgBackupArtifacts:
    """Build dump and checksum paths for a backup run."""
    dump_file = Path(backup_dir) / build_dump_filename(database=database, now=now)
    return PgBackupArtifacts(
        dump_file=dump_file,
        checksum_file=build_checksum_file_path(dump_file),
    )


def build_pg_isready_command(
    host: str,
    port: int,
    user: str,
    database: str,
    timeout_seconds: int,
) -> list[str]:
    """Build a pg_isready command using explicit args."""
    return [
        "pg_isready",
        "-h",
        host,
        "-p",
        str(port),
        "-U",
        user,
        "-d",
        database,
        "-t",
        str(timeout_seconds),
    ]


def build_pg_dump_command(
    host: str,
    port: int,
    user: str,
    database: str,
    dump_file: Path,
    compression_level: int,
    timeout_seconds: int | None = None,
) -> list[str]:
    """Build a pg_dump command using PostgreSQL custom format."""
    del timeout_seconds
    return [
        "pg_dump",
        "-h",
        host,
        "-p",
        str(port),
        "-U",
        user,
        "-F",
        "c",
        "-Z",
        str(compression_level),
        "-v",
        "-f",
        str(dump_file),
        database,
    ]


def build_pg_restore_list_command(dump_file: Path) -> list[str]:
    """Build a pg_restore list command for dump verification."""
    return ["pg_restore", "-l", str(dump_file)]


def calculate_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Calculate a SHA-256 digest for a file."""
    digest = hashlib.sha256()
    with Path(file_path).open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def list_dump_files(backup_dir: Path) -> list[Path]:
    """List dump files in a backup directory."""
    return sorted(
        [path for path in Path(backup_dir).iterdir() if path.name.endswith(".dump")],
        key=lambda path: path.name,
    )


def get_latest_dump_file(backup_dir: Path) -> Path | None:
    """Return the most recent dump file by mtime, if any."""
    latest_dump: Path | None = None
    latest_mtime: float | None = None

    for dump_file in list_dump_files(backup_dir):
        dump_mtime = dump_file.stat().st_mtime
        if latest_mtime is None or dump_mtime > latest_mtime:
            latest_dump = dump_file
            latest_mtime = dump_mtime

    return latest_dump


def get_latest_dump_size_bytes(backup_dir: Path) -> int:
    """Return the size of the newest dump file, if any."""
    latest_dump = get_latest_dump_file(backup_dir)
    if latest_dump is None:
        return 0
    return latest_dump.stat().st_size


def find_backup_files_to_prune(
    backup_dir: Path,
    retention_days: int,
    now: datetime,
) -> list[Path]:
    """Return expired dump artifacts for pruning."""
    cutoff = now - timedelta(days=retention_days)
    candidates: list[Path] = []

    for dump_file in list_dump_files(backup_dir):
        dump_mtime = datetime.fromtimestamp(dump_file.stat().st_mtime)
        if dump_mtime >= cutoff:
            continue

        candidates.append(dump_file)
        checksum_file = build_checksum_file_path(dump_file)
        if checksum_file.exists():
            candidates.append(checksum_file)

    return candidates

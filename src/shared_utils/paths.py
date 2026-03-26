"""Repo-root path helpers for host and Docker execution."""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]


def get_repo_root() -> Path:
    """Return the absolute path to the repository root."""
    return _REPO_ROOT


def resolve_repo_relative_path(path: str | Path) -> Path:
    """Resolve absolute paths directly and repo-relative paths from the repo root."""
    resolved_path = Path(path).expanduser()
    if resolved_path.is_absolute():
        return resolved_path
    return get_repo_root() / resolved_path


def resolve_required_repo_file(
    path: str | Path,
    *,
    description: str,
    example_path: str | Path | None = None,
) -> Path:
    """Resolve a required file path and raise a repo-aware error when it is missing."""
    resolved_path = resolve_repo_relative_path(path)
    if resolved_path.exists():
        return resolved_path

    message = (
        f"{description} not found at {resolved_path}. "
        f"Relative paths are resolved from the repo root {get_repo_root()}."
    )
    if example_path is not None:
        resolved_example_path = resolve_repo_relative_path(example_path)
        message += (
            f" Copy {resolved_example_path} to {resolved_path}, "
            "or pass an explicit absolute or repo-relative path."
        )
    raise FileNotFoundError(message)

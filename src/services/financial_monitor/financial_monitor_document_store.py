"""Document-store helpers for financial monitor source files."""

from pathlib import Path


def ensure_document_store_dirs(workspace_dir: Path) -> dict[str, Path]:
    """Create and return the document-store directories for a workspace."""
    directories = {
        "raw_root": workspace_dir / "raw",
        "tdnet_raw_dir": workspace_dir / "raw" / "tdnet",
        "edinet_raw_dir": workspace_dir / "raw" / "edinet",
        "manifests_dir": workspace_dir / "manifests",
    }
    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)
    return directories


def build_source_document_path(
    workspace_dir: Path,
    source: str,
    document_id: str,
    filename: str,
) -> Path:
    """Build a deterministic raw-document path for a source document."""
    directories = ensure_document_store_dirs(workspace_dir)
    raw_dir_key = f"{source}_raw_dir"
    if raw_dir_key not in directories:
        raise ValueError(f"Unsupported source: {source}")
    return directories[raw_dir_key] / document_id / Path(filename).name


def write_source_document(
    workspace_dir: Path,
    source: str,
    document_id: str,
    filename: str,
    content: bytes,
) -> Path:
    """Write source bytes to the deterministic raw-document path."""
    output_path = build_source_document_path(
        workspace_dir=workspace_dir,
        source=source,
        document_id=document_id,
        filename=filename,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(content)
    return output_path

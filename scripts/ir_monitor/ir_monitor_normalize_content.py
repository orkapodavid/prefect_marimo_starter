"""Bridge script for webchanges custom execute filters."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from services.ir_monitor.normalizers import NORMALIZERS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normalizer", required=True)
    parser.add_argument("--page-url", required=True)
    parser.add_argument("--input-file")
    return parser.parse_args()


def _configure_stdio() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def main() -> int:
    _configure_stdio()
    args = parse_args()

    normalizer = NORMALIZERS.get(args.normalizer)
    if normalizer is None:
        sys.stderr.write(f"Unknown normalizer: {args.normalizer}\n")
        return 1

    if args.input_file:
        content = Path(args.input_file).read_text(encoding="utf-8")
    else:
        content = sys.stdin.read()

    sys.stdout.write(normalizer(content, args.page_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Batch unpack all clock resource files in a folder."""
from __future__ import annotations

import argparse
from pathlib import Path

from unpack import main as unpack_main


def _iter_sources(folder: Path, pattern: str) -> list[Path]:
    sources = sorted(folder.glob(pattern))
    return [p for p in sources if p.is_file()]


def run() -> None:
    parser = argparse.ArgumentParser(description="Batch unpack ClockXXXXX_res files in a folder")
    parser.add_argument("folder", type=Path, help="Folder containing ClockXXXXX_res files")
    parser.add_argument(
        "-p",
        "--pattern",
        default="Clock*_res",
        help="Glob pattern to match resource files (default: Clock*_res)",
    )
    parser.add_argument(
        "-o",
        "--out-root",
        type=Path,
        help="Optional output root; defaults to creating *_unpacked next to each source",
    )
    parser.add_argument(
        "--min-chunk-len",
        type=int,
        default=16,
        help="Minimum length to treat a pair as image chunk",
    )
    parser.add_argument(
        "--area-num-count",
        type=int,
        default=4,
        help="Assumed count for dataType==112 area_num list",
    )
    args = parser.parse_args()

    folder = args.folder
    if not folder.is_dir():
        raise SystemExit(f"Folder not found: {folder}")

    sources = _iter_sources(folder, args.pattern)
    if not sources:
        raise SystemExit(f"No files matched {args.pattern} in {folder}")

    for src in sources:
        out_dir = None
        if args.out_root:
            out_dir = args.out_root / f"{src.name}_unpacked"
        argv = [
            "unpack.py",
            str(src),
            "--min-chunk-len",
            str(args.min_chunk_len),
            "--area-num-count",
            str(args.area_num_count),
        ]
        if out_dir:
            argv += ["-o", str(out_dir)]

        # Reuse unpack.py CLI
        import sys

        old_argv = sys.argv
        try:
            sys.argv = argv
            unpack_main()
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    run()

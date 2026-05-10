#!/usr/bin/env python3
"""Recursively import a directory of text/markdown files into zvec-kb.

Each file becomes one snippet; the file stem is added as a tag so you can
trace results back to source. Files larger than --max-bytes are skipped to
keep embeddings meaningful (long docs degrade single-vector recall).

Examples:
    kb batch-import ~/notes
    kb batch-import ./docs --ext .md .txt .org --tag imported
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import kb  # type: ignore  # noqa: E402


def _normalize_exts(raw: list[str]) -> set[str]:
    out: set[str] = set()
    for e in raw:
        e = e.lower()
        out.add(e if e.startswith(".") else f".{e}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="import a folder of text files into zvec-kb"
    )
    parser.add_argument("path", help="directory to scan recursively")
    parser.add_argument(
        "--ext",
        nargs="+",
        default=[".md", ".txt"],
        help="file extensions to import (default: .md .txt)",
    )
    parser.add_argument(
        "--tag", action="append", default=[], help="extra tag (repeatable)"
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=20_000,
        help="skip files larger than this (single-vector recall degrades on long docs)",
    )
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    exts = _normalize_exts(args.ext)
    files = [f for f in root.rglob("*") if f.is_file() and f.suffix.lower() in exts]
    print(f"found {len(files)} candidate file(s) under {root}")

    added = 0
    skipped_large = 0
    errors = 0
    for f in files:
        try:
            if f.stat().st_size > args.max_bytes:
                skipped_large += 1
                print(f"  [skip-large] {f.relative_to(root)}")
                continue
            text = f.read_text(encoding="utf-8").strip()
            if not text:
                continue
            tags = list(args.tag) + [f.stem]
            if kb.cmd_add(text, tags) == 0:
                added += 1
        except Exception as exc:
            errors += 1
            print(f"  [error] {f}: {type(exc).__name__}: {exc}")

    print(
        f"\nimported {added}/{len(files)} "
        f"(skipped-large={skipped_large}, errors={errors})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

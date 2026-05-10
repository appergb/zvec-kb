#!/usr/bin/env python3
"""Bulk-add snippets from positional args, a file, or stdin.

Examples:
    kb quick-add "first note" "second note" --tag demo
    kb quick-add --file notes.txt --tag imported
    cat notes.txt | kb quick-add --tag piped

Each line / arg becomes one snippet. Blank lines are skipped.
Idempotent: re-adding the same text is a no-op (sha256-based id).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import kb  # type: ignore  # noqa: E402


def _gather(args: argparse.Namespace) -> list[str]:
    snippets: list[str] = list(args.texts or [])
    if args.file:
        for line in Path(args.file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                snippets.append(line)
    if not snippets and not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.strip()
            if line:
                snippets.append(line)
    return snippets


def main() -> int:
    parser = argparse.ArgumentParser(description="bulk-add snippets to zvec-kb")
    parser.add_argument("texts", nargs="*", help="snippets passed as positional args")
    parser.add_argument(
        "--file", help="read snippets from a file (one per line, blanks skipped)"
    )
    parser.add_argument(
        "--tag", action="append", default=[], help="tag (repeatable)"
    )
    args = parser.parse_args()

    snippets = _gather(args)
    if not snippets:
        print(
            "no input — pass texts as args, --file PATH, or pipe via stdin",
            file=sys.stderr,
        )
        return 2

    added = 0
    for text in snippets:
        if kb.cmd_add(text, args.tag) == 0:
            added += 1
    print(f"\n{added}/{len(snippets)} processed (existing ids skipped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

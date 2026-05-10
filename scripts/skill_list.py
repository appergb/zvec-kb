#!/usr/bin/env python3
"""List skills uploaded to zvec-kb.

Filters texts.jsonl for entries tagged "skill" and prints one row each
with name, source path, and a short preview. Use --detail to dump the
indexed snippet for one or all skills.

Examples:
    kb skill-list
    kb skill-list --detail
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import kb  # type: ignore  # noqa: E402


def _tag_value(tags: list[str] | None, prefix: str) -> str:
    for t in tags or []:
        if t.startswith(prefix):
            return t[len(prefix):]
    return "?"


def main() -> int:
    parser = argparse.ArgumentParser(description="list skills uploaded to zvec-kb")
    parser.add_argument(
        "--detail",
        action="store_true",
        help="dump the indexed snippet for each skill",
    )
    args = parser.parse_args()

    texts = kb._load_texts()
    skills = [r for r in texts.values() if "skill" in (r.get("tags") or [])]

    print(f"total skills: {len(skills)}")
    for r in skills:
        tags = r.get("tags") or []
        name = _tag_value(tags, "name:")
        src = _tag_value(tags, "src:")
        body = r.get("text") or ""
        if args.detail:
            print(f"\n=== {name} ===")
            print(f"id:   {r['id']}")
            print(f"src:  {src}")
            print(body)
        else:
            preview = body.replace("\n", " ").strip()
            if len(preview) > 100:
                preview = preview[:100] + "…"
            print(f"  [{r['id']}] {name}")
            print(f"    src: {src}")
            print(f"    {preview}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

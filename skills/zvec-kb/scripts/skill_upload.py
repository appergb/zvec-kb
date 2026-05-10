#!/usr/bin/env python3
"""Upload a Claude Code skill folder into zvec-kb.

Reads <dir>/SKILL.md, parses the YAML frontmatter for `name` and
`description`, and stores `name + description` as one snippet so the skill
becomes semantically searchable alongside ordinary notes.

Why we embed only the frontmatter, not the whole body: the embedding model
truncates at ~512 tokens, and `description` is already the field designed
to summarize when a skill should trigger — embedding it gives the best
recall for "find me a skill that does X" queries. The full body stays on
disk at the source path (recorded in the `src:` tag).

Examples:
    kb skill-upload ~/.claude/skills/zvec-kb
    kb skill-upload ./my-new-skill --extra-tag draft
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import kb  # type: ignore  # noqa: E402


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (meta_dict, body) from a SKILL.md.

    Tolerates missing/malformed frontmatter — returns ({}, text) in that case
    so the caller can still index something useful.
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, parts[2].lstrip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="upload a Claude Code skill folder into zvec-kb"
    )
    parser.add_argument("path", help="skill directory containing SKILL.md")
    parser.add_argument(
        "--extra-tag",
        action="append",
        default=[],
        help="extra tag (repeatable)",
    )
    args = parser.parse_args()

    skill_dir = Path(args.path).expanduser().resolve()
    if not skill_dir.is_dir():
        print(f"not a directory: {skill_dir}", file=sys.stderr)
        return 2
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        print(f"no SKILL.md in {skill_dir}", file=sys.stderr)
        return 2

    raw = md.read_text(encoding="utf-8")
    meta, _body = _parse_frontmatter(raw)
    name = str(meta.get("name") or skill_dir.name).strip()
    desc = str(meta.get("description") or "").strip()
    if not desc:
        print(
            f"warning: SKILL.md has no description frontmatter — "
            f"using folder name only",
            file=sys.stderr,
        )

    snippet = f"{name}\n\n{desc}".strip()
    tags = ["skill", f"name:{name}", f"src:{skill_dir}"] + list(args.extra_tag)
    return kb.cmd_add(snippet, tags)


if __name__ == "__main__":
    sys.exit(main())

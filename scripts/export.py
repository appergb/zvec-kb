#!/usr/bin/env python3
"""Dump all stored snippets (id + text + tags) as JSON to stdout.

Vectors are not exported — they can be regenerated from text. The JSONL
sidecar at ZVEC_KB_DIR/texts.jsonl is the source of truth.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import kb  # type: ignore  # noqa: E402


def main() -> int:
    texts = kb._load_texts()
    json.dump(list(texts.values()), sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

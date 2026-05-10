#!/usr/bin/env python3
"""Semantic search with optional JSON output.

Examples:
    kb quick-search "如何让 LLM 写代码靠谱"
    kb quick-search "embedding model" --topk 10 --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import kb  # type: ignore  # noqa: E402


def _search_json(query: str, topk: int) -> int:
    import zvec

    coll = kb._get_collection()
    vec = kb._get_model().encode(query).tolist()
    results = coll.query(zvec.VectorQuery("embedding", vector=vec), topk=topk)
    texts = kb._load_texts()
    payload = [
        {
            "id": r.id,
            "distance": float(r.score),
            "text": (texts.get(r.id) or {}).get("text"),
            "tags": (texts.get(r.id) or {}).get("tags") or [],
        }
        for r in results
    ]
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="semantic search zvec-kb")
    parser.add_argument("q", help="query text")
    parser.add_argument("--topk", type=int, default=5)
    parser.add_argument(
        "--json", action="store_true", help="emit JSON instead of human-readable text"
    )
    args = parser.parse_args()

    if args.json:
        return _search_json(args.q, args.topk)
    return kb.cmd_query(args.q, args.topk)


if __name__ == "__main__":
    sys.exit(main())

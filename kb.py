#!/usr/bin/env python3
"""ZVEC-backed lightweight personal knowledge base.

Add text -> auto-embed via sentence-transformers -> store vector in ZVEC + text in sidecar JSONL.
Query text -> embed -> ZVEC HNSW cosine search -> join with sidecar to return original text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

DATA_DIR = Path(os.environ.get(
    "ZVEC_KB_DIR",
    str(Path.home() / ".claude" / "data" / "zvec-kb"),
))
COLLECTION_PATH = DATA_DIR / "collection"
SIDECAR_PATH = DATA_DIR / "texts.jsonl"
MODEL_NAME = os.environ.get(
    "ZVEC_KB_MODEL",
    "paraphrase-multilingual-MiniLM-L12-v2",
)
DIMENSION = 384
COLLECTION_NAME = "knowledge_base"

_model = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection
    import zvec
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if COLLECTION_PATH.exists():
        _collection = zvec.open(str(COLLECTION_PATH))
    else:
        schema = zvec.CollectionSchema(
            name=COLLECTION_NAME,
            vectors=[
                zvec.VectorSchema(
                    name="embedding",
                    data_type=zvec.DataType.VECTOR_FP32,
                    dimension=DIMENSION,
                    index_param=zvec.HnswIndexParam(metric_type=zvec.MetricType.COSINE),
                ),
            ],
        )
        _collection = zvec.create_and_open(path=str(COLLECTION_PATH), schema=schema)
    return _collection


def _make_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _load_texts() -> dict:
    if not SIDECAR_PATH.exists():
        return {}
    texts: dict = {}
    with SIDECAR_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            texts[row["id"]] = row
    return texts


def _append_text(doc_id: str, text: str, tags: list) -> None:
    SIDECAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SIDECAR_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"id": doc_id, "text": text, "tags": tags}, ensure_ascii=False) + "\n")


def _rewrite_sidecar(texts: dict) -> None:
    tmp = SIDECAR_PATH.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in texts.values():
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(SIDECAR_PATH)


def cmd_add(text: str, tags: list) -> int:
    import zvec
    doc_id = _make_id(text)
    texts = _load_texts()
    if doc_id in texts:
        print(f"[skip] already exists: {doc_id}")
        return 0
    vec = _get_model().encode(text).tolist()
    coll = _get_collection()
    coll.insert([zvec.Doc(id=doc_id, vectors={"embedding": vec})])
    _append_text(doc_id, text, tags)
    print(f"[ok] added {doc_id} ({len(text)} chars, tags={tags or []})")
    return 0


def cmd_query(q: str, topk: int) -> int:
    import zvec
    coll = _get_collection()
    vec = _get_model().encode(q).tolist()
    results = coll.query(zvec.VectorQuery("embedding", vector=vec), topk=topk)
    texts = _load_texts()
    if not results:
        print("(no results)")
        return 0
    for r in results:
        meta = texts.get(r.id, {})
        snippet = (meta.get("text") or "<missing>").replace("\n", " ")
        if len(snippet) > 200:
            snippet = snippet[:200] + "…"
        tag_str = f" [{','.join(meta.get('tags') or [])}]" if meta.get("tags") else ""
        print(f"[dist={r.score:.3f}] {r.id}{tag_str}  {snippet}")
    return 0


def cmd_list() -> int:
    texts = _load_texts()
    print(f"total: {len(texts)}")
    for doc_id, row in texts.items():
        snippet = (row.get("text") or "").replace("\n", " ")
        if len(snippet) > 80:
            snippet = snippet[:80] + "…"
        tag_str = f" [{','.join(row.get('tags') or [])}]" if row.get("tags") else ""
        print(f"  {doc_id}{tag_str}  {snippet}")
    return 0


def cmd_delete(doc_id: str) -> int:
    coll = _get_collection()
    texts = _load_texts()
    if doc_id not in texts:
        print(f"[skip] not found in sidecar: {doc_id}")
        return 1
    coll.delete(ids=doc_id)
    del texts[doc_id]
    _rewrite_sidecar(texts)
    print(f"[ok] deleted {doc_id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="zvec-kb")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="add a text snippet")
    p_add.add_argument("text")
    p_add.add_argument("--tag", action="append", default=[])

    p_query = sub.add_parser("query", help="semantic search")
    p_query.add_argument("q")
    p_query.add_argument("--topk", type=int, default=5)

    sub.add_parser("list", help="list all stored snippets")

    p_delete = sub.add_parser("delete", help="delete by id")
    p_delete.add_argument("id")

    args = parser.parse_args()
    if args.cmd == "add":
        return cmd_add(args.text, args.tag)
    if args.cmd == "query":
        return cmd_query(args.q, args.topk)
    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "delete":
        return cmd_delete(args.id)
    return 1


if __name__ == "__main__":
    sys.exit(main())

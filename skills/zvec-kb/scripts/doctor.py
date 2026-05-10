#!/usr/bin/env python3
"""Verify zvec-kb is installed correctly.

Checks: imports → model load → end-to-end ZVEC round-trip in a temp dir.
Exits non-zero on any failure so install.sh and CI can rely on it.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Callable


def _check(label: str, fn: Callable[[], None]) -> bool:
    try:
        fn()
        print(f"  [ok] {label}")
        return True
    except Exception as exc:
        print(f"  [fail] {label}: {type(exc).__name__}: {exc}")
        return False


def _import_zvec() -> None:
    import zvec

    _ = zvec.DataType.VECTOR_FP32


def _import_st() -> None:
    from sentence_transformers import SentenceTransformer

    _ = SentenceTransformer


def _round_trip() -> None:
    """Insert one vector into a throwaway collection and query it back."""
    import zvec
    from sentence_transformers import SentenceTransformer

    model_name = os.environ.get(
        "ZVEC_KB_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
    )

    with tempfile.TemporaryDirectory() as td:
        schema = zvec.CollectionSchema(
            name="doctor_check",
            vectors=[
                zvec.VectorSchema(
                    name="embedding",
                    data_type=zvec.DataType.VECTOR_FP32,
                    dimension=384,
                    index_param=zvec.HnswIndexParam(
                        metric_type=zvec.MetricType.COSINE
                    ),
                )
            ],
        )
        coll = zvec.create_and_open(path=str(Path(td) / "c"), schema=schema)
        model = SentenceTransformer(model_name)
        vec = model.encode("hello world").tolist()
        coll.insert([zvec.Doc(id="abc", vectors={"embedding": vec})])
        results = coll.query(zvec.VectorQuery("embedding", vector=vec), topk=1)
        if not results or results[0].id != "abc":
            raise AssertionError(f"unexpected query result: {results}")


def main() -> int:
    print("zvec-kb doctor")
    ok = True
    ok &= _check("import zvec", _import_zvec)
    ok &= _check("import sentence_transformers", _import_st)
    ok &= _check("end-to-end ZVEC round-trip", _round_trip)
    print("ok" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

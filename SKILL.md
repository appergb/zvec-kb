---
name: zvec-kb
description: Lightweight personal vector knowledge base using Alibaba's ZVEC (in-process vector DB, "the SQLite of vector databases"). Save short text snippets/notes/facts and retrieve them later by semantic similarity via local sentence-transformers embedding. Use when the user wants to "save this for later", "remember that X", "search my notes", "what did I save about Y", or build an incremental personal KB. Differs from qmd (which scans markdown files) by accepting individual text snippets through a CLI.
---

# ZVEC KB — Lightweight Personal Vector Knowledge Base

Minimal CLI-driven knowledge base built on:
- **ZVEC** (`alibaba/zvec`) — embedded in-process vector DB with HNSW + COSINE
- **sentence-transformers** (`paraphrase-multilingual-MiniLM-L12-v2`, 384-d, zh/en bilingual) — local text→vector

Storage path: `~/.claude/data/zvec-kb/` (override with env `ZVEC_KB_DIR`).

## When to Activate

- User says: "记下这个 / 存到知识库 / save this / remember that ..."
- User asks: "我之前存过什么关于 X / search my notes / what did I save about ..."
- Incremental personal facts or snippets that need semantic recall later

## When NOT to Use

- File-scanning over markdown corpora → use `qmd` (already indexes 955 docs)
- Cross-session conversation memory → use auto-memory at `~/.claude/projects/*/memory/`
- Entities + relations graph → use `mcp__memory__`

## CLI Usage

All operations run via Bash. Substitute `python3` for whichever python has zvec installed.

```bash
# Save a snippet (idempotent — same text → same id, no duplicates)
python3 ~/.claude/skills/zvec-kb/kb.py add "Karpathy's 4 LLM coding rules: think before coding, simplicity first, surgical changes, goal-driven execution" --tag rules

# Search semantically
python3 ~/.claude/skills/zvec-kb/kb.py query "如何让 LLM 写代码更靠谱" --topk 5

# List everything
python3 ~/.claude/skills/zvec-kb/kb.py list

# Delete by id (returned from list/query)
python3 ~/.claude/skills/zvec-kb/kb.py delete <id>
```

## One-time Setup

```bash
pip install zvec sentence-transformers
```

First `add` or `query` triggers a one-time ~120MB model download to
`~/.cache/huggingface/`. Subsequent calls load from cache (~2s startup).

## Architecture (KISS)

| Component | Storage | Why |
|---|---|---|
| Vectors | ZVEC collection at `~/.claude/data/zvec-kb/collection/` | HNSW search, sub-ms lookup |
| Original text + tags | Sidecar `~/.claude/data/zvec-kb/texts.jsonl` | ZVEC's STRING scalar field is undocumented in README; sidecar avoids assumptions and stays debuggable (just `cat` it) |
| IDs | `sha256(text)[:16]` | Idempotent — re-inserting same text is a no-op |

## Score semantics

Query results print `[dist=0.461]` — that is **cosine distance** (lower = closer match).
Despite ZVEC docs calling it "similarity score", it's actually distance: `dist ≈ 1 - cos_sim`.
Best matches appear first; ZVEC sorts ascending automatically.

## Trade-offs (read before extending)

- **Single collection** — no namespacing/projects yet. Add via `--collection` arg if needed later.
- **Append-only sidecar** — `delete` rewrites the JSONL; not atomic if interrupted mid-write. Fine for personal use.
- **No metadata filtering** — query is pure cosine similarity. If you later need `WHERE tag=...`, switch to ZVEC's native scalar fields with `delete_by_filter`.
- **No re-ranking** — unlike `qmd`, this is single-pass vector recall only. Good enough for short snippet KB.

## Alternative embedding backend (v2 idea)

ZVEC 0.3+ ships built-in embedding functions: `DefaultLocalDenseEmbedding`,
`DefaultLocalSparseEmbedding`, `OpenAIDenseEmbedding`, `BM25EmbeddingFunction`.
A future v2 could drop sentence-transformers and use ZVEC's native pipeline,
shrinking the dependency footprint by ~700MB (no torch). Current v1 keeps
sentence-transformers for explicit control over the model.

## ZVEC API gotchas (discovered during smoke testing — not in README)

- Collection `name` requires ≥3 chars matching `[A-Za-z0-9_]+` regex (`"kb"` is rejected).
- `zvec.create_and_open(path, schema)` errors if path already exists. For
  reopening an existing collection, use `zvec.open(path)` instead.
- `collection.query(...)` returns `Doc` objects (use `.id` and `.score`),
  not dicts as the README claims.

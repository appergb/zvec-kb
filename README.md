# zvec-kb

Lightweight personal vector knowledge base, packaged as a Claude Code **skill**.

- **Storage:** [`alibaba/zvec`](https://github.com/alibaba/zvec) — embedded in-process vector DB ("the SQLite of vector databases"), HNSW + cosine.
- **Embedding:** [`sentence-transformers`](https://github.com/UKPLab/sentence-transformers) (`paraphrase-multilingual-MiniLM-L12-v2`, 384-d, zh/en bilingual).
- **Surface:** a Bash-callable Python CLI + a `SKILL.md` so Claude Code auto-invokes it on phrases like "save this", "记下这个", "search my notes", "我之前存过什么".

## Install on a fresh machine

```bash
# 1. Clone into Claude's skill directory so Claude auto-discovers it
mkdir -p ~/.claude/skills
git clone https://github.com/appergb/zvec-kb.git ~/.claude/skills/zvec-kb

# 2. Install Python deps (~700MB — pulls torch + transformers; one-time)
pip install -r ~/.claude/skills/zvec-kb/requirements.txt
```

That's it. The first `add` or `query` triggers a one-time ~120MB
multilingual embedding-model download cached at `~/.cache/huggingface/`.

## Usage

```bash
# Save a snippet (idempotent — same text → same id, no duplicates)
python3 ~/.claude/skills/zvec-kb/kb.py add "Karpathy's 4 LLM coding rules" --tag rules

# Search semantically (works across zh/en)
python3 ~/.claude/skills/zvec-kb/kb.py query "如何让 AI 写代码靠谱" --topk 5

# List everything
python3 ~/.claude/skills/zvec-kb/kb.py list

# Delete by id (returned from list/query)
python3 ~/.claude/skills/zvec-kb/kb.py delete <id>
```

Data lives at `~/.claude/data/zvec-kb/` (override with `ZVEC_KB_DIR=...`).
Embedding model can be swapped with `ZVEC_KB_MODEL=...` (must match `DIMENSION` in `kb.py`).

## How it stores data (KISS)

| Component | Location | Purpose |
|---|---|---|
| Vectors + HNSW index | `~/.claude/data/zvec-kb/collection/` | Sub-ms cosine recall via ZVEC |
| Original text + tags | `~/.claude/data/zvec-kb/texts.jsonl` | `cat`-able sidecar; ZVEC's STRING scalar field is undocumented in v0.3.1 |
| Doc IDs | `sha256(text)[:16]` | Idempotent inserts |

## Claude Code integration

When this skill is in `~/.claude/skills/zvec-kb/`, Claude Code reads `SKILL.md`
at session start. The description triggers on phrases like:

- "记下这个 / 存到知识库 / save this / remember that ..."
- "我之前存过什么关于 X / search my notes / what did I save about ..."

Claude then runs the `kb.py` commands above via Bash. No MCP server, no daemon.

## Trade-offs

- **Single collection, no namespacing.** Add `--collection` later if needed.
- **Append-only sidecar.** `delete` rewrites the JSONL atomically via `tmp + replace`.
- **No metadata filtering.** Pure cosine recall. Switch to ZVEC scalar fields + `delete_by_filter` if you need `WHERE tag=...`.
- **No re-ranking.** Single-pass vector recall. For files-on-disk corpora, prefer [qmd](https://github.com/example/qmd) which adds BM25 + HyDE.

## ZVEC v0.3.1 API gotchas (verified by smoke test)

The official README is incomplete or inaccurate on these points. Documenting
here so contributors don't re-discover them:

1. Collection `name` requires ≥3 chars matching `[A-Za-z0-9_]+`. `"kb"` is rejected.
2. `zvec.create_and_open(path, schema)` errors if the path already exists.
   For reopening a persisted collection, use `zvec.open(path)`.
3. `collection.query(...)` returns `Doc` objects (use `.id`, `.score`),
   not dicts as the README claims.
4. Score is **cosine distance** (lower = closer), not similarity, despite
   "ranked by similarity score" in the docs.
5. ZVEC ships built-in embedding functions (`DefaultLocalDenseEmbedding`,
   `OpenAIDenseEmbedding`, `BM25EmbeddingFunction`). A future v2 of this
   skill could drop the sentence-transformers dependency entirely.

## License

MIT — see [LICENSE](LICENSE).

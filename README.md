# zvec-kb

Lightweight personal vector knowledge base, packaged as a Claude Code **skill**.

- **Storage:** [`alibaba/zvec`](https://github.com/alibaba/zvec) — embedded in-process vector DB ("the SQLite of vector databases"), HNSW + cosine.
- **Embedding:** [`sentence-transformers`](https://github.com/UKPLab/sentence-transformers) (`paraphrase-multilingual-MiniLM-L12-v2`, 384-d, zh/en bilingual).
- **Surface:** a Bash-callable Python CLI + a `SKILL.md` so Claude Code auto-invokes it on phrases like "save this", "记下这个", "search my notes", "我之前存过什么".

## Repository layout

This repo follows the standard "skills monorepo" pattern — each skill lives under `skills/<name>/`:

```
zvec-kb/                       # this repo
├── README.md
├── LICENSE
└── skills/
    └── zvec-kb/               # the skill itself; copy this to ~/.claude/skills/zvec-kb
        ├── SKILL.md
        ├── kb.py
        ├── requirements.txt
        ├── bin/kb             # universal launcher (auto-uses isolated venv)
        └── scripts/           # install.sh, doctor.py, quick_*, batch_import, skill_*
```

## Install on a fresh machine (one-click)

```bash
# 1. Get the skill folder into Claude's skill directory
mkdir -p ~/.claude/skills
git clone https://github.com/appergb/zvec-kb.git /tmp/zvec-kb-repo
cp -r /tmp/zvec-kb-repo/skills/zvec-kb ~/.claude/skills/zvec-kb
rm -rf /tmp/zvec-kb-repo

# 2. One-click installer — creates an isolated venv, installs deps,
#    pre-warms the embedding model, runs an end-to-end doctor check
bash ~/.claude/skills/zvec-kb/scripts/install.sh
```

That's it. The installer pulls torch + transformers (~700MB, one-time) into
`~/.claude/data/zvec-kb/.venv/`, downloads the multilingual embedding model
(~120MB, cached at `~/.cache/huggingface/`), and verifies a full ZVEC
round-trip before exiting.

## Usage

Every command goes through the launcher — it auto-resolves the isolated venv:

```bash
KB=~/.claude/skills/zvec-kb/bin/kb

# Save a snippet (idempotent — same text → same id, no duplicates)
"$KB" add "Karpathy's 4 LLM coding rules" --tag rules

# Search semantically (works across zh/en)
"$KB" query "如何让 AI 写代码靠谱" --topk 5

# Bulk add / batch import / JSON output / export / delete
"$KB" quick-add --file notes.txt --tag imported
"$KB" batch-import ~/notes --ext .md .txt
"$KB" quick-search "embedding" --json --topk 10
"$KB" export > kb.json
"$KB" delete <id>

# Skill registry — index your Claude Code skill folders
"$KB" skill-upload ~/.claude/skills/some-skill
"$KB" skill-list
"$KB" query "find me a skill that does X"

# Health check / re-install
"$KB" doctor
"$KB" install
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

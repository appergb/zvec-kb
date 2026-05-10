---
name: zvec-kb
description: Lightweight personal vector knowledge base. Save short text snippets/notes/facts and retrieve them later by semantic similarity, locally and privately, via Alibaba's ZVEC (in-process vector DB) + sentence-transformers (multilingual zh/en embeddings). Use this skill whenever the user wants to "save this", "记下这个", "存到知识库", "remember that X", "我之前存过什么", "search my notes", "what did I save about Y", or any incremental personal-KB workflow. Also use it when the user asks to bulk-import a folder of notes/markdown into a searchable KB, to install/initialize a personal vector KB, or to register/upload/list/find Claude Code skills (commands `kb skill-upload`, `kb skill-list`). Prefer this over auto-memory when the user explicitly wants searchable snippets, and over qmd when there are no on-disk markdown files yet.
---

# ZVEC KB — Lightweight Personal Vector Knowledge Base

A CLI-driven, in-process vector KB. No daemon, no MCP server, no cloud.

- **Vectors:** [`alibaba/zvec`](https://github.com/alibaba/zvec) — embedded, HNSW + COSINE
- **Embeddings:** [`sentence-transformers`](https://github.com/UKPLab/sentence-transformers) — `paraphrase-multilingual-MiniLM-L12-v2` (384-d, zh/en)
- **Storage:** `~/.claude/data/zvec-kb/` (override with env `ZVEC_KB_DIR`)

## When to activate

Trigger this skill when the user says any of:

- "记下这个 / 存到知识库 / 把这个存起来 / 加到我的笔记"
- "save this / remember that / add this to my notes"
- "我之前存过什么关于 X / 找一下我之前记的 …"
- "search my notes / what did I save about Y"
- "import my markdown folder into a vector KB"
- "set up a local vector knowledge base / 安装/初始化 zvec-kb"

## When NOT to use

- Scanning a corpus of markdown files already on disk → use `qmd` (BM25 + HyDE)
- Cross-session conversational memory → use the harness auto-memory at `~/.claude/projects/*/memory/`
- Entity + relation graph storage → use `mcp__memory__*`

## Entry point — always use the launcher

The skill ships a launcher at `bin/kb` that uses an isolated venv (no system-Python pollution). Resolve its absolute path once and reuse:

```bash
KB="$HOME/.claude/skills/zvec-kb/bin/kb"
```

If the user copied this skill elsewhere, substitute that path. The launcher prints a clear error if the venv is missing, telling you to run install.

## One-time install (one command)

```bash
bash ~/.claude/skills/zvec-kb/scripts/install.sh
```

This:
1. creates a venv at `$ZVEC_KB_DIR/.venv` (default `~/.claude/data/zvec-kb/.venv`)
2. installs `requirements.txt` (zvec + sentence-transformers + torch, ~700MB)
3. pre-warms the embedding model (~120MB download once)
4. runs `doctor.py` to verify a full ZVEC round-trip

If the user just cloned the repo and asks to "set it up" or "make it work", run that command. If `$KB doctor` fails after install, surface the error verbatim — don't guess.

## Common workflows

### Save a snippet

```bash
"$KB" add "Karpathy's 4 LLM coding rules: think before coding, simplicity first, surgical changes, goal-driven execution" --tag rules
```

Idempotent: re-adding the same text is a no-op (id = `sha256(text)[:16]`).

### Bulk-add (multiple snippets at once)

```bash
"$KB" quick-add "first note" "second note" --tag demo
"$KB" quick-add --file notes.txt --tag imported
cat notes.txt | "$KB" quick-add --tag piped
```

### Search

```bash
"$KB" query "如何让 LLM 写代码靠谱" --topk 5      # human-readable
"$KB" quick-search "embedding model" --json --topk 10   # machine-readable
```

`distance` is **cosine distance** (lower = closer). ZVEC sorts ascending automatically — first result is best.

### Import a folder of notes

```bash
"$KB" batch-import ~/notes                              # .md + .txt by default
"$KB" batch-import ./docs --ext .md .txt .org --tag imported
```

Each file becomes one snippet; the file stem becomes a tag for traceability. Files larger than 20KB are skipped (single-vector recall degrades on long docs — for those, prefer `qmd`).

### List, export, delete

```bash
"$KB" list                              # short summary of every snippet
"$KB" export > kb.json                  # full dump (id + text + tags), no vectors
"$KB" delete <id>                       # delete by id (returned from list/query)
```

### Manage Claude Code skills (upload + display)

zvec-kb doubles as a tiny searchable registry for Claude Code skill folders. Use this when the user says "把这个技能存起来 / register this skill / upload my skill folder / 列一下我存过哪些 skill / find a skill that does X".

```bash
"$KB" skill-upload ~/.claude/skills/zvec-kb            # ingest a skill (reads its SKILL.md)
"$KB" skill-upload ./my-new-skill --extra-tag draft    # extra tags allowed
"$KB" skill-list                                       # short list (id, name, source)
"$KB" skill-list --detail                              # dump indexed snippet for each
"$KB" query "skill that does file uploads" --topk 5    # also finds skills (they live in the same KB)
```

What gets indexed: the skill's `name` + `description` from its SKILL.md frontmatter — that is the same field Claude uses to decide when to trigger a skill, so it gives the best recall for "find me a skill that does X" queries. The full body stays on disk; the source folder path is recorded in the `src:` tag for traceability.

### Health check

```bash
"$KB" doctor
```

Three green checks = everything works. Use this whenever a query suddenly fails — it isolates whether the problem is imports, model, or ZVEC.

## Architecture (KISS)

| Component | Storage | Why |
|---|---|---|
| Vectors + HNSW index | `$ZVEC_KB_DIR/collection/` | sub-ms cosine recall |
| Original text + tags  | `$ZVEC_KB_DIR/texts.jsonl` | `cat`-able sidecar; ZVEC's STRING scalar field is undocumented in v0.3.1 |
| IDs                  | `sha256(text)[:16]`        | idempotent inserts |
| Python deps          | `$ZVEC_KB_DIR/.venv/`      | isolated; uninstall == `rm -rf $ZVEC_KB_DIR/.venv` |

## Trade-offs (read before extending)

- **Single collection, no namespacing.** Add a `--collection` arg if you need projects.
- **Append-only sidecar.** `delete` rewrites JSONL atomically via `tmp + replace`.
- **No metadata filtering.** Pure cosine. For `WHERE tag=...`, switch to ZVEC scalar fields + `delete_by_filter`.
- **No re-ranking.** Single-pass vector recall. For files-on-disk corpora, prefer `qmd` (BM25 + HyDE).

## ZVEC v0.3.1 API gotchas (verified by `doctor.py`)

The official README is incomplete on these points:

1. Collection `name` requires ≥3 chars matching `[A-Za-z0-9_]+`. `"kb"` is rejected.
2. `zvec.create_and_open(path, schema)` errors if the path already exists. To reopen, use `zvec.open(path)`.
3. `collection.query(...)` returns `Doc` objects (use `.id`, `.score`), not dicts.
4. `Doc.score` is **cosine distance** (lower = closer), not similarity.
5. ZVEC ships built-in embedding functions (`DefaultLocalDenseEmbedding`, `OpenAIDenseEmbedding`, `BM25EmbeddingFunction`). A future v2 could drop sentence-transformers entirely.

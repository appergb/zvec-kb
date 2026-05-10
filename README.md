# zvec-kb

**Lightweight personal vector knowledge base — fast, local, persistent — packaged as a Claude Code skill.**

**轻量级个人向量知识库 —— 快速、本地、持久化 —— 打包成 Claude Code 技能。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Built on [`alibaba/zvec`](https://github.com/alibaba/zvec) (in-process vector DB, "the SQLite of vector databases") + [`sentence-transformers`](https://github.com/UKPLab/sentence-transformers) (multilingual zh/en embeddings, 384-d).

---

## English

### What it is

`zvec-kb` is a CLI-driven personal vector knowledge base. Feed it short text — notes, facts, code rules, skill descriptions — and retrieve them later by **semantic** similarity rather than keyword match. Everything runs locally in a single Python process. No daemon, no server, no Docker, no cloud.

It also ships as a Claude Code **skill**, so Claude auto-triggers it on phrases like *"save this"*, *"记下这个"*, *"我之前存过什么关于…"*, *"search my notes"*, and routes the right CLI command for you. You can equally use it standalone from any terminal.

### Why zvec-kb? (vs other vector DBs)

| Project | Form factor | Cold start | Persistence | Setup | Best for |
|---|---|---|---|---|---|
| **zvec-kb** | **Embedded CLI** | **~2s (model load)** | **RocksDB + JSONL on local disk** | **`bash install.sh`** | **Personal KB, single user** |
| Chroma (server) | HTTP server | seconds (server boot) | DuckDB / SQLite | `pip install` + `chroma run` | Prototyping, multi-client |
| Qdrant | gRPC / HTTP server | seconds (Rust binary) | Custom segments | `docker run` or binary | Production, multi-tenant |
| Weaviate | Server | seconds–tens (JVM-ish stack) | Custom segments | `docker compose up` | GraphQL-native search |
| Milvus | Distributed | minutes | etcd + object store | k8s / Docker stack | Billion-scale |
| pgvector | Postgres extension | depends on PG | Postgres pages | install extension | Apps already on Postgres |
| sqlite-vec | SQLite extension | sub-second | SQLite file | `pip install` + load | Embedded apps, mobile |
| LanceDB | Embedded | ~2s | Lance columnar files | `pip install` | Analytics on vectors |
| FAISS | Library only (no DB layer) | sub-second | None — you persist yourself | `pip install` | Custom pipelines |

**Where zvec-kb wins (the three claims):**

- **Fast.** In-process means **zero IPC and zero network**. Once the embedding model is loaded into memory (~2s, paid once per process), HNSW lookups are sub-millisecond on personal-scale data. There is no server to boot, no auth handshake, no JSON-over-HTTP round-trip, and no cold-start tax on every query.
- **Physical persistence.** Data lives at well-known paths under `~/.claude/data/zvec-kb/`: vectors in a RocksDB-backed ZVEC collection, original text + tags in a `cat`-able `texts.jsonl` sidecar. Nothing is hidden inside a service's opaque storage. You can `grep` your KB, `tar` it, `rsync` it across machines, inspect it without a client. Restart your laptop — data is still there.
- **Lightweight.** The skill itself is < 50 KB of Python. The install adds an isolated venv (~700 MB, mostly torch + tokenizers — required by sentence-transformers) plus a one-time ~120 MB embedding model. **No Docker, no Kubernetes, no Postgres, no Redis, no service to keep alive.** Uninstall = `rm -rf ~/.claude/skills/zvec-kb ~/.claude/data/zvec-kb`.

**Where zvec-kb is NOT the right tool:**

- Multi-user / multi-tenant production workloads → Qdrant / Milvus
- Billion-scale vectors with replication → Milvus
- Scanning a corpus of markdown files already on disk with BM25 + HyDE re-ranking → use `qmd`
- Mobile / embedded apps → `sqlite-vec`
- You already run Postgres and want one less moving part → `pgvector`

### Repository layout (skills monorepo)

```
zvec-kb/                       # this repo
├── README.md
├── LICENSE
└── skills/
    └── zvec-kb/               # the skill — copy this folder to ~/.claude/skills/zvec-kb
        ├── SKILL.md           # Claude Code skill manifest (triggers + how-to)
        ├── kb.py              # core CLI: add / query / list / delete
        ├── requirements.txt   # zvec + sentence-transformers
        ├── bin/
        │   └── kb             # universal launcher (auto-resolves the venv)
        └── scripts/
            ├── install.sh         # one-click installer
            ├── doctor.py          # health check (imports → model → ZVEC round-trip)
            ├── quick_add.py       # bulk add (args / --file / stdin)
            ├── quick_search.py    # semantic search with optional JSON output
            ├── batch_import.py    # recursive import of .md / .txt folder
            ├── export.py          # dump everything as JSON
            ├── skill_upload.py    # register a Claude Code skill folder
            └── skill_list.py      # list registered skills
```

### One-click install

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/appergb/zvec-kb.git /tmp/zvec-kb-repo
cp -r /tmp/zvec-kb-repo/skills/zvec-kb ~/.claude/skills/zvec-kb
rm -rf /tmp/zvec-kb-repo
bash ~/.claude/skills/zvec-kb/scripts/install.sh
```

What the installer does:

1. creates an isolated venv at `~/.claude/data/zvec-kb/.venv` (no system-Python pollution)
2. installs `zvec` + `sentence-transformers` + `torch` (~700 MB, one-time)
3. pre-warms the multilingual embedding model (~120 MB, cached at `~/.cache/huggingface/`)
4. runs `doctor.py` to verify the full pipeline — imports, model load, end-to-end ZVEC round-trip

### Usage

All commands flow through the launcher; it auto-uses the isolated venv:

```bash
KB=~/.claude/skills/zvec-kb/bin/kb

# --- core ---
"$KB" add "Karpathy's 4 LLM coding rules" --tag rules
"$KB" query "如何让 LLM 写代码靠谱" --topk 5      # works across zh/en
"$KB" list
"$KB" delete <id>

# --- bulk / batch ---
"$KB" quick-add "snippet 1" "snippet 2" --tag demo    # positional args
"$KB" quick-add --file notes.txt --tag imported       # from file
cat notes.txt | "$KB" quick-add --tag piped           # from stdin
"$KB" batch-import ~/notes --ext .md .txt --tag imported

# --- machine-readable output ---
"$KB" quick-search "embedding model" --json --topk 10
"$KB" export > kb.json

# --- skill registry: index your Claude Code skill folders ---
"$KB" skill-upload ~/.claude/skills/some-skill
"$KB" skill-list                                      # short list
"$KB" skill-list --detail                             # full snippet for each
"$KB" query "find me a skill that does X"             # skills are searchable too

# --- ops ---
"$KB" doctor          # imports → model → ZVEC round-trip
"$KB" install         # re-run installer (idempotent)
"$KB" help
```

### Storage layout

| Component | Path | Purpose |
|---|---|---|
| Vectors + HNSW index | `~/.claude/data/zvec-kb/collection/` | Sub-ms cosine recall via ZVEC (RocksDB-backed) |
| Original text + tags | `~/.claude/data/zvec-kb/texts.jsonl` | `cat`-able sidecar, one JSON object per line |
| Doc IDs | `sha256(text)[:16]` | Idempotent inserts — re-adding the same text is a no-op |
| Python deps | `~/.claude/data/zvec-kb/.venv/` | Isolated; system Python untouched |

Override the data location with `ZVEC_KB_DIR=/custom/path`. Override the embedding model with `ZVEC_KB_MODEL=...` (must produce 384-dim vectors to match the schema in `kb.py`).

### Score semantics

Query results print `[dist=0.461]` — that is **cosine distance** (lower means closer). Despite upstream ZVEC docs calling it "similarity score", it is actually distance: `dist ≈ 1 − cos_sim`. Best matches appear first; ZVEC sorts ascending automatically.

### Trade-offs (read before extending)

- **Single collection, no namespacing.** Add a `--collection` arg if you need projects.
- **Append-only sidecar.** `delete` rewrites JSONL atomically via `tmp + replace`; safe but not concurrent-write-friendly.
- **No metadata filtering.** Pure cosine recall. For `WHERE tag=...` filters, switch to ZVEC scalar fields + `delete_by_filter`.
- **No re-ranking.** Single-pass vector recall. Fine for short snippets; for long docs prefer a tool with BM25 + HyDE re-ranking.
- **Single embedding model.** Swappable via `ZVEC_KB_MODEL`, but must stay 384-dim to match the schema.

### License

MIT — see [LICENSE](LICENSE).

---

## 中文版

### 是什么

`zvec-kb` 是一个 CLI 驱动的个人向量知识库。把短文本（笔记、事实、规则、技能描述）喂进去，之后用**语义**相似度而不是关键字精确匹配把它们检索出来。整套东西在单个 Python 进程里跑——没有守护进程、没有服务器、没有 Docker、没有云端。

它同时打包成一个 Claude Code **技能**，所以你说"记下这个 / 我之前存过什么关于… / search my notes"这类话时 Claude 会自动触发并选对 CLI 命令。当然你也可以直接在任何 terminal 里独立使用。

### 为什么用 zvec-kb（对比其他向量数据库）

| 项目 | 形态 | 冷启动 | 持久化 | 安装步骤 | 适合场景 |
|---|---|---|---|---|---|
| **zvec-kb** | **嵌入式 CLI** | **~2 秒（加载模型）** | **本地 RocksDB + JSONL** | **`bash install.sh`** | **个人知识库、单用户** |
| Chroma (server) | HTTP 服务 | 数秒（启服务） | DuckDB / SQLite | `pip install` + `chroma run` | 原型开发、多客户端 |
| Qdrant | gRPC / HTTP 服务 | 数秒（Rust 二进制） | 自定义段 | `docker run` 或二进制 | 生产、多租户 |
| Weaviate | 服务 | 数秒到数十秒 | 自定义段 | `docker compose up` | GraphQL 风格检索 |
| Milvus | 分布式 | 数分钟 | etcd + 对象存储 | k8s / Docker 栈 | 十亿级规模 |
| pgvector | Postgres 扩展 | 取决于 PG | Postgres 数据页 | 装扩展 | 已经在用 Postgres 的应用 |
| sqlite-vec | SQLite 扩展 | 亚秒级 | SQLite 文件 | `pip install` 后 load | 嵌入式 / 移动应用 |
| LanceDB | 嵌入式 | ~2 秒 | Lance 列式文件 | `pip install` | 向量分析 |
| FAISS | 仅库（无 DB 层） | 亚秒级 | 无 — 自己负责持久化 | `pip install` | 自定义 pipeline |

**zvec-kb 的三个核心优势：**

- **速度快。** 进程内意味着**零 IPC、零网络**。embedding 模型加载完一次（~2 秒，一个进程内只付一次）后，个人规模数据的 HNSW 检索是亚毫秒级的。没有服务启动、没有鉴权握手、没有 JSON-over-HTTP 的来回，每次查询都没有冷启动开销。
- **物理保存。** 数据存放在 `~/.claude/data/zvec-kb/` 下的明确路径里：向量在 RocksDB 支撑的 ZVEC 集合中，原文 + 标签在可以直接 `cat` 的 `texts.jsonl` 旁路文件中。没有任何东西藏在某个服务不透明的存储里。你可以 `grep` 你的知识库、`tar` 打包、`rsync` 到别的机器、不用任何客户端就能查看。重启电脑数据照常在。
- **轻量。** 技能本身 < 50 KB Python。安装会加一个独立的 venv（~700 MB，主要是 torch + tokenizers，sentence-transformers 强依赖）和一次性的 ~120 MB embedding 模型。**没有 Docker、没有 Kubernetes、没有 Postgres、没有 Redis、不需要常驻任何服务。** 卸载 = `rm -rf ~/.claude/skills/zvec-kb ~/.claude/data/zvec-kb`。

**zvec-kb 不适合的场景：**

- 多用户 / 多租户的生产工作负载 → 用 Qdrant / Milvus
- 十亿级向量加多副本 → 用 Milvus
- 已经在磁盘上的整个 markdown 文件库做扫描 + BM25 + HyDE 重排 → 用 `qmd`
- 移动 / 嵌入式应用 → 用 `sqlite-vec`
- 已经在跑 Postgres、想少一个组件 → 用 `pgvector`

### 仓库结构（skills monorepo 布局）

```
zvec-kb/                       # 本仓库
├── README.md
├── LICENSE
└── skills/
    └── zvec-kb/               # 技能本体——把这个文件夹复制到 ~/.claude/skills/zvec-kb
        ├── SKILL.md           # Claude Code 技能清单（触发条件 + 用法）
        ├── kb.py              # 核心 CLI：add / query / list / delete
        ├── requirements.txt   # zvec + sentence-transformers
        ├── bin/
        │   └── kb             # 通用 launcher（自动定位 venv）
        └── scripts/
            ├── install.sh         # 一键安装
            ├── doctor.py          # 健康检查（imports → 模型 → ZVEC 闭环）
            ├── quick_add.py       # 批量 add（args / --file / stdin）
            ├── quick_search.py    # 语义搜索，可选 JSON 输出
            ├── batch_import.py    # 递归导入 .md / .txt 文件夹
            ├── export.py          # 导出全部为 JSON
            ├── skill_upload.py    # 注册一个 Claude Code 技能文件夹
            └── skill_list.py      # 列出已注册技能
```

### 一键安装

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/appergb/zvec-kb.git /tmp/zvec-kb-repo
cp -r /tmp/zvec-kb-repo/skills/zvec-kb ~/.claude/skills/zvec-kb
rm -rf /tmp/zvec-kb-repo
bash ~/.claude/skills/zvec-kb/scripts/install.sh
```

安装脚本的工作：

1. 在 `~/.claude/data/zvec-kb/.venv` 创建独立 venv（不污染系统 Python）
2. 装 `zvec` + `sentence-transformers` + `torch`（~700 MB，一次性）
3. 预热多语言 embedding 模型（~120 MB，缓存到 `~/.cache/huggingface/`）
4. 跑 `doctor.py` 端到端验证整条流水线 —— imports、模型加载、ZVEC 闭环

### 用法

所有命令都通过 launcher 走，自动使用独立 venv：

```bash
KB=~/.claude/skills/zvec-kb/bin/kb

# --- 核心 ---
"$KB" add "Karpathy 的四条 LLM 编码原则" --tag rules
"$KB" query "如何让 LLM 写代码靠谱" --topk 5     # 中英双语都能搜
"$KB" list
"$KB" delete <id>

# --- 批量 ---
"$KB" quick-add "片段 1" "片段 2" --tag demo            # 位置参数
"$KB" quick-add --file notes.txt --tag imported          # 从文件
cat notes.txt | "$KB" quick-add --tag piped              # 从 stdin
"$KB" batch-import ~/notes --ext .md .txt --tag imported

# --- 机器可读输出 ---
"$KB" quick-search "embedding 模型" --json --topk 10
"$KB" export > kb.json

# --- 技能注册（把 Claude Code 技能文件夹索引进来） ---
"$KB" skill-upload ~/.claude/skills/some-skill
"$KB" skill-list                                          # 短列表
"$KB" skill-list --detail                                 # 每条完整内容
"$KB" query "find me a skill that does X"                 # 技能也能被搜到

# --- 运维 ---
"$KB" doctor          # imports → 模型 → ZVEC 闭环
"$KB" install         # 重跑安装（幂等）
"$KB" help
```

### 存储布局

| 组件 | 路径 | 作用 |
|---|---|---|
| 向量 + HNSW 索引 | `~/.claude/data/zvec-kb/collection/` | ZVEC 亚毫秒级余弦检索（RocksDB 支撑） |
| 原文 + 标签 | `~/.claude/data/zvec-kb/texts.jsonl` | 可直接 `cat` 的旁路文件，每行一个 JSON |
| 文档 ID | `sha256(text)[:16]` | 幂等插入——同一段文本再 add 是 no-op |
| Python 依赖 | `~/.claude/data/zvec-kb/.venv/` | 独立环境，不动系统 Python |

用 `ZVEC_KB_DIR=/自定义路径` 覆盖数据目录。用 `ZVEC_KB_MODEL=...` 切换 embedding 模型（必须输出 384 维向量以匹配 `kb.py` 中的 schema）。

### 评分含义

查询结果打印 `[dist=0.461]`——这是**余弦距离**，越小越接近。尽管 ZVEC 上游文档把它叫做 "similarity score"，它其实是距离：`dist ≈ 1 − cos_sim`。最佳匹配在最前；ZVEC 自动按升序排列。

### 取舍（扩展前先读）

- **单 collection，无命名空间。** 需要项目隔离时加一个 `--collection` 参数。
- **追加式旁路文件。** `delete` 会通过 `tmp + replace` 原子重写 JSONL；安全但不适合并发写。
- **不支持元数据过滤。** 只走纯余弦召回。如果需要 `WHERE tag=...`，切换到 ZVEC 的 scalar field + `delete_by_filter`。
- **不做重排。** 单轮向量召回。短笔记够用；长文档建议用带 BM25 + HyDE 重排的工具。
- **单一 embedding 模型。** 可通过 `ZVEC_KB_MODEL` 切换，但必须保持 384 维以匹配 schema。

### 许可

MIT —— 见 [LICENSE](LICENSE)。

#!/usr/bin/env bash
# One-click installer for zvec-kb.
#   - creates an isolated venv at $ZVEC_KB_DIR/.venv (default ~/.claude/data/zvec-kb/.venv)
#   - installs requirements.txt
#   - pre-warms the multilingual embedding model so the first query is fast
#   - runs doctor.py to verify the install end-to-end
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="${ZVEC_KB_DIR:-$HOME/.claude/data/zvec-kb}"
VENV="$DATA_DIR/.venv"
PYTHON="${PYTHON:-python3}"

echo "==> skill   : $SKILL_DIR"
echo "==> data    : $DATA_DIR"
echo "==> venv    : $VENV"

mkdir -p "$DATA_DIR"

if [ ! -x "$VENV/bin/python" ]; then
    echo "==> creating venv with $PYTHON"
    "$PYTHON" -m venv "$VENV"
fi

echo "==> upgrading pip"
"$VENV/bin/pip" install --quiet --upgrade pip

echo "==> installing requirements (pulls torch + transformers ~700MB on first run)"
"$VENV/bin/pip" install -r "$SKILL_DIR/requirements.txt"

echo "==> pre-warming embedding model (one-time ~120MB download to ~/.cache/huggingface)"
"$VENV/bin/python" - <<'PY'
import os
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
from sentence_transformers import SentenceTransformer
name = os.environ.get("ZVEC_KB_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
SentenceTransformer(name)
print(f"model ready: {name}")
PY

echo "==> running doctor"
"$VENV/bin/python" "$SKILL_DIR/scripts/doctor.py"

echo
echo "ok — zvec-kb is ready."
echo
echo "use it (via launcher):"
echo "  $SKILL_DIR/bin/kb add \"some note\" --tag demo"
echo "  $SKILL_DIR/bin/kb query \"a question\""
echo
echo "or directly:"
echo "  $VENV/bin/python $SKILL_DIR/kb.py list"

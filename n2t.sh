#!/usr/bin/env bash
# Build a PDF from a Notion HTML export.
# Usage: ./n2t.sh [export.zip | page.html]
# Requires: pip install -e .  (or: pip install notion2tex)
#
# Outputs (inside extracted export folder):
#   automata_clean.html  — cleaned HTML
#   automata.tex         — LaTeX source
#   automata.pdf         — final PDF

set -euo pipefail
cd "$(dirname "$0")"

INPUT="${1:?Usage: ./n2t.sh export.zip}"

if command -v notion2tex >/dev/null 2>&1; then
  exec notion2tex "$INPUT"
fi

PYTHON=".venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

exec "$PYTHON" -m notion2tex "$INPUT"

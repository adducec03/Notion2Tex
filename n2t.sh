#!/usr/bin/env bash
# Build a PDF from a Notion HTML export.
# Usage: ./n2t.sh [input.html]
# Example: ./n2t.sh automata.html
#
# Outputs (for automata.html):
#   automata_clean.html  — cleaned HTML
#   automata.tex         — LaTeX source
#   automata.pdf         — final PDF

set -euo pipefail
cd "$(dirname "$0")"

HTML="${1:-automata.html}"
BASE="${HTML%.html}"
CLEAN_HTML="${BASE}_clean.html"
TEX="${BASE}.tex"
PDF="${BASE}.pdf"

PYTHON=".venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

if [[ ! -f "$HTML" ]]; then
  echo "Error: file not found: $HTML" >&2
  exit 1
fi

echo "==> 1/4 Clean HTML"
"$PYTHON" clean_html.py "$HTML"

echo "==> 2/4 Pandoc → LaTeX"
pandoc "$CLEAN_HTML" -f html -t latex -s -o "$TEX"

echo "==> 3/4 Fix LaTeX"
"$PYTHON" fix_latex.py "$TEX"

echo "==> 4/4 Build PDF (2 passes)"
rm -f "${BASE}.aux" "${BASE}.toc" "${BASE}.out"
pdflatex -interaction=nonstopmode "$TEX" >/dev/null
pdflatex -interaction=nonstopmode "$TEX" >/dev/null

echo ""
echo "Done: $PDF"

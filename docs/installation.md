# Installation

## Requirements

| Tool | Purpose |
|------|---------|
| **Python 3.10+** | CLI and HTML/LaTeX processing |
| **Pandoc 3.x** | HTML → LaTeX |
| **pdflatex** (TeX Live or MacTeX) | PDF build |

Notion2Tex does **not** bundle Pandoc or TeX. Install them separately on your system.

### Pandoc

Download and install from the [Pandoc installation guide](https://pandoc.org/installing.html).

Verify:

```bash
pandoc --version
```

### TeX (pdflatex)

Install [TeX Live](https://www.tug.org/texlive/) (Linux/Windows) or [MacTeX](https://www.tug.org/mactex/) (macOS). A minimal TeX Live install is usually enough.

Verify:

```bash
pdflatex --version
```

If compilation fails with a missing `.sty` file, install the package with TeX Live Manager, for example:

```bash
tlmgr install soul ulem float booktabs tabularx hyperref
```

Notion2Tex tries `soul` for strikethrough, then `ulem`, then disables strikeout if neither is available.

## Install from PyPI

```bash
pip install notion2tex
notion2tex --check
```

The package page is [pypi.org/project/notion2tex](https://pypi.org/project/notion2tex/).

Upgrade to a newer release:

```bash
pip install -U notion2tex
```

## Install for development

Clone the repository and install in editable mode:

```bash
git clone https://github.com/adducec03/Notion2Tex.git
cd Notion2Tex
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

Optional: install documentation build tools:

```bash
pip install -r docs/requirements.txt
mkdocs serve   # preview at http://127.0.0.1:8000
```

## Optional wrapper script

After a development install, you can use the thin shell wrapper:

```bash
chmod +x n2t.sh   # once
./n2t.sh Export.zip
```

This calls the same `notion2tex` CLI as `pip install notion2tex`.

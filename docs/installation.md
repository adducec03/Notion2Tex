# Installation

## Requirements

| Tool | Purpose |
|------|---------|
| **Python 3.10+** | CLI and HTML/LaTeX processing |
| **Pandoc 3.x** | HTML → LaTeX — needs to be **fairly recent** (see below) |
| **pdflatex** (TeX Live or MacTeX) | PDF build, with `tcolorbox`, `framed`, `soul`/`ulem`, `lmodern` |

Notion2Tex does **not** bundle Pandoc or TeX. Install them separately on your system, or use the [Docker image](#docker-alternative) below, which pins known-good versions of both.

### Pandoc

Download and install from the [Pandoc installation guide](https://pandoc.org/installing.html).

Verify:

```bash
pandoc --version
```

!!! warning "Use a recent Pandoc, not your Linux distro's packaged one"
    The pipeline relies on a Lua filter and MathML-based math handling that need a **recent** Pandoc build. Debian/Ubuntu's `apt install pandoc` can lag far behind upstream and will silently drop colored text, underline, columns, callouts, or math — with no error, just missing formatting. Install directly from [pandoc.org](https://pandoc.org/installing.html) (or GitHub Releases) instead of the distro package if you hit this.

### TeX (pdflatex)

Install [TeX Live](https://www.tug.org/texlive/) (Linux/Windows) or [MacTeX](https://www.tug.org/mactex/) (macOS). A minimal TeX Live install is usually enough.

Verify:

```bash
pdflatex --version
```

If compilation fails with a missing `.sty` file, install the package with TeX Live Manager, for example:

```bash
tlmgr install soul ulem float booktabs tabularx hyperref tcolorbox framed
```

Notion2Tex tries `soul` for strikethrough/underline, then `ulem`, then disables strikeout if neither is available. Callouts, quotes, and web-bookmark cards additionally need `tcolorbox` and `framed`.

!!! note "Debian/Ubuntu package split"
    On Debian-based systems, `soul`/`ulem` ship in the `texlive-plain-generic` package rather than `texlive-latex-extra` — install it explicitly if `tlmgr` isn't available (`apt install texlive-plain-generic`).

## Docker alternative

No local Pandoc/TeX install needed — the bundled `Dockerfile` builds an image with a pinned, known-good Pandoc release and a full TeX toolchain:

```bash
docker build -t notion2tex:latest .
docker compose run notion2tex --check
docker compose run notion2tex Export.zip
```

See [DOCKER.md](https://github.com/adducec03/Notion2Tex/blob/main/DOCKER.md) in the repository for volume mounts and more examples.

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

# Installation

Pick one of three ways to run Notion2Tex, roughly from easiest to most involved.

## Option 1: Docker (recommended)

No Python, Pandoc, or TeX to install — everything runs inside a container. You only need [Docker](https://docs.docker.com/get-docker/).

```bash
curl -O https://raw.githubusercontent.com/adducec03/Notion2Tex/main/scripts/notion2tex-docker.sh
chmod +x notion2tex-docker.sh
./notion2tex-docker.sh /path/to/Export.zip
```

Windows (PowerShell):

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/adducec03/Notion2Tex/main/scripts/notion2tex-docker.ps1 -OutFile notion2tex-docker.ps1
./notion2tex-docker.ps1 C:\Users\me\Downloads\Export.zip
```

The script downloads the image on first use and writes the PDF right next to your input file. Converting more than once? Install the script into a folder already on your `PATH` (e.g. `sudo mv notion2tex-docker.sh /usr/local/bin/notion2tex`) and `notion2tex` becomes a regular command from any directory — see [DOCKER.md](https://github.com/adducec03/Notion2Tex/blob/main/DOCKER.md) for the exact steps and more options.

## Option 2: pip

```bash
pip install notion2tex
notion2tex --check
```

This installs the CLI, but **not** Pandoc or a TeX distribution — install those separately:

- [Pandoc](https://pandoc.org/installing.html) — use a recent release, not an old distro package.
- [TeX Live](https://www.tug.org/texlive/) (Linux/Windows) or [MacTeX](https://www.tug.org/mactex/) (macOS) for `pdflatex`.

`notion2tex --check` confirms both are found. If something's missing or outdated, see [Troubleshooting](troubleshooting.md).

Upgrade later with:

```bash
pip install -U notion2tex
```

## Option 3: From source

For contributing, or to try unreleased changes.

```bash
git clone https://github.com/adducec03/Notion2Tex.git
cd Notion2Tex
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
notion2tex --check
```

Same Pandoc/TeX requirements as the pip install above. Run the test suite with `pytest`.

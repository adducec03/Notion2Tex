# Docker Setup Guide for Notion2Tex

This guide explains how to use Notion2Tex with Docker, avoiding the need to manually set up a virtual environment and install dependencies.

## Prerequisites

- **Docker** ([install](https://docs.docker.com/install/))
- **Docker Compose** (included with Docker Desktop) — only needed if you're working from a clone of this repo

## Just want to convert a file? (no clone needed)

The image is published to GitHub Container Registry (`ghcr.io/adducec03/notion2tex`) on every push to `main`. Download the wrapper script for your OS and point it at any file on disk — nothing else to install, no repo checkout required:

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

The script mounts the input file's own folder into the container and runs notion2tex there, so `Export.pdf`/`.tex`/`.log` land right next to `Export.zip` — no separate `exports/`/`output/` folders to manage. It also always pulls the latest `:latest` image before running (`docker run --pull always`), so every push to `main` is picked up automatically without you having to remember to `docker pull`. Extra CLI flags pass straight through:

```bash
./notion2tex-docker.sh /path/to/Export.zip --dark
./notion2tex-docker.sh /path/to/Page.html --tex-only
```

Pin a specific version instead of `latest`:

```bash
NOTION2TEX_IMAGE=ghcr.io/adducec03/notion2tex:v1.2.3 ./notion2tex-docker.sh /path/to/Export.zip
```

### Use it as a plain `notion2tex` command

The script doesn't care about its own name or location — install it once into a directory already on your `PATH` and it behaves exactly like a native command from then on, from any folder, with no repo, no `docker-compose`, and nothing left to download again:

```bash
sudo curl -fsSL https://raw.githubusercontent.com/adducec03/Notion2Tex/main/scripts/notion2tex-docker.sh -o /usr/local/bin/notion2tex
sudo chmod +x /usr/local/bin/notion2tex
```

```bash
notion2tex --config
notion2tex Export.zip
notion2tex Export.zip --dark
```

(No `sudo`/write access to `/usr/local/bin`? Use a directory you own that's already on `PATH`, e.g. `~/.local/bin` or `~/bin`.) Windows: save `notion2tex-docker.ps1` (e.g. as `notion2tex.ps1`) into a folder already on your `PATH`, or add a function to your PowerShell profile that calls it.

### How the published image stays up to date

[`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml) rebuilds and republishes `ghcr.io/adducec03/notion2tex:latest` on every push to `main` (merged PRs included), plus versioned tags (e.g. `:1.2.3` and `:1.2`, no `v` prefix) whenever a `v1.2.3`-style git tag is pushed — the same tag that also triggers a matching PyPI release, see [Releasing a new version](https://adducec03.github.io/Notion2Tex/development/#releasing-a-new-version-pypi-docker-together) in the docs. Pushes to other branches, or open PRs that haven't merged yet, don't trigger it. Because the wrapper scripts always `docker pull` before running, you get the newest `main` automatically — no manual `docker pull`/rebuild step needed.

The rest of this guide covers building the image yourself from a clone of the repo (useful for development, or if you've changed the Dockerfile).

## Working from a clone of the repo

### 1. Build the Docker Image

```bash
docker-compose build
```

Or build manually:

```bash
docker build -t notion2tex:latest .
```

### 2. Verify Installation

Check that `pandoc` and `pdflatex` are available inside the container:

```bash
docker-compose run notion2tex --check
```

### 3. Prepare Your Files

Create an `exports/` directory in the project root and place your Notion export ZIP file there:

```bash
mkdir -p exports output
cp ~/Downloads/Export.zip exports/
```

### 4. Convert to PDF

Run the conversion using docker-compose:

```bash
docker-compose run notion2tex Export.zip
```

Output files (`Export.tex`, `Export.pdf`, `Export.log`) will be saved in the `exports/` directory (inside the container's `/app/exports`).

### 5. Retrieve the PDF

The `output/` directory is also mounted, so you can place files there if needed:

```bash
docker-compose run notion2tex Export.zip --extract-dir /app/output
```

## Usage Examples

### Convert a ZIP file

```bash
docker-compose run notion2tex Export.zip
```

### Convert a single HTML file

```bash
docker-compose run notion2tex Page.html
```

### LaTeX only (no PDF compilation)

```bash
docker-compose run notion2tex Export.zip --tex-only
```

### Show compiler output

```bash
docker-compose run notion2tex Export.zip -v
```

### Dark mode

```bash
docker-compose run notion2tex Export.zip --dark
```

### Display help

```bash
docker-compose run notion2tex --help
```

## Manual Docker Commands

If you prefer to use Docker directly without docker-compose:

### Build

```bash
docker build -t notion2tex:latest .
```

### Run

```bash
docker run --rm -v $(pwd)/exports:/app/exports notion2tex:latest Export.zip
```

Or with output directory:

```bash
docker run --rm \
  -v $(pwd)/exports:/app/exports \
  -v $(pwd)/output:/app/output \
  notion2tex:latest Export.zip
```

## Troubleshooting

### `docker: unauthorized` / `denied` when pulling `ghcr.io/adducec03/notion2tex`

A freshly-published GHCR package defaults to **private**, even though the repo itself is public. This is fixed on the publisher's side, not the puller's: go to the GitHub profile's Packages tab → `notion2tex` → Package settings → Danger Zone → Change visibility → **Public**. Repo maintainers: this only needs doing once, right after the `Publish Docker image` workflow's first successful run.

### `--config`'s interactive menu doesn't render correctly (or shows a clear "needs a real terminal" error)

The arrow-key menu needs a real terminal. `docker-compose run` already allocates one (`stdin_open`/`tty` are set in `docker-compose.yml`), and the `notion2tex-docker.sh`/`.ps1` wrapper scripts add `-it` automatically whenever your own shell session is interactive — so this is normally not something you need to think about. If you're scripting a plain `docker run` yourself instead of using one of those, add `-it` explicitly:

```bash
docker run --rm -it -v "$(pwd):/data" -w /data ghcr.io/adducec03/notion2tex:latest --config
```

Running `--config` in a genuinely non-interactive context (CI, a piped/redirected shell) fails fast with an explicit error rather than hanging — that's expected; `--config` isn't meant to run unattended.

### Image builds successfully but `notion2tex --check` fails

This means dependencies are missing. Verify the Dockerfile installs:
- `pandoc` 
- `texlive-latex-base` and related packages
- Python 3.12+ with pip

### "Command not found: notion2tex"

Ensure the image was built after editing `pyproject.toml` or `notion2tex/` files:

```bash
docker-compose build --no-cache
```

### PDF not generated, only .tex file

Run with `-v` to see pdflatex output:

```bash
docker-compose run notion2tex Export.zip -v
```

Missing LaTeX packages can be added to the Dockerfile's `apt-get install` list. Note that `soul`/`ulem` (strikethrough/underline) and `lmodern` come from separate Debian packages (`texlive-plain-generic`, `lmodern`), not `texlive-latex-extra` — if you trim the package list, keep those explicitly or those features silently stop rendering.

### `Package babel Error: Unknown option 'italian'` (or another `--lang` code)

The babel core package is present, but the language-specific file (`italian.ldf`) isn't — it ships in its own Debian package, `texlive-lang-italian`, already in the provided Dockerfile. If you trimmed the package list, add it back for whichever `--lang` codes you need (`english` ships with babel's core, no extra package required).

### Colored text, columns, callouts, or math are missing/plain in the PDF

The Dockerfile installs Pandoc directly from a pinned GitHub release (`PANDOC_VERSION` build arg, currently `3.10.1`) instead of Debian's packaged `pandoc`, because that packaged version is too old to run the Lua filter and MathML-based math handling this pipeline relies on. If you changed the Dockerfile to use `apt install pandoc` instead, that's almost certainly why formatting is missing — revert to the GitHub-release install, or bump `PANDOC_VERSION` to a newer release if needed.

## Image Size Optimization

The multi-stage Dockerfile minimizes the final image size (~1.5 GB with full TeX):
- Builder stage compiles dependencies (discarded)
- Final stage contains only runtime requirements

To reduce further, use `texlive-latex-minimal` instead of `texlive-latex-extra`:

Edit the Dockerfile and replace:
```dockerfile
texlive-latex-extra \
```

with:
```dockerfile
texlive-latex-minimal \
# Then add missing packages as needed:
# texlive-fonts-recommended \
# texlive-latex-base \
# tlmgr install <package>
```

`tcolorbox` and `framed` (callouts, quotes, bookmark cards) and `soul`/`ulem` (strikethrough/underline, from `texlive-plain-generic`) currently ride along with `texlive-latex-extra`/`texlive-plain-generic` — if you trim to `texlive-latex-minimal`, add those back explicitly or those features silently stop rendering.

## Docker Compose Services

The `docker-compose.yml` defines a single `notion2tex` service with:
- Auto-building from Dockerfile
- Volume mounts for inputs (`./exports`) and outputs (`./output`)
- Interactive TTY for CLI arguments

To modify working directory or add environment variables, edit `docker-compose.yml`.

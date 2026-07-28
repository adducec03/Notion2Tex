# Docker Setup Guide for Notion2Tex

This guide explains how to use Notion2Tex with Docker, avoiding the need to manually set up a virtual environment and install dependencies.

## Prerequisites

- **Docker** ([install](https://docs.docker.com/install/))
- **Docker Compose** (included with Docker Desktop)

## Quick Start

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

Missing LaTeX packages can be added to the Dockerfile's `texlive-latex-extra` section.

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

## Docker Compose Services

The `docker-compose.yml` defines a single `notion2tex` service with:
- Auto-building from Dockerfile
- Volume mounts for inputs (`./exports`) and outputs (`./output`)
- Interactive TTY for CLI arguments

To modify working directory or add environment variables, edit `docker-compose.yml`.

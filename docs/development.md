# Development

## Project structure

```
Notion2Tex/
├── notion2tex/           # Installable package
│   ├── cli.py            # Command-line interface
│   ├── pipeline.py       # Full build orchestration
│   ├── zip_export.py     # Extract Notion .zip, find main .html
│   ├── clean_html.py     # Step 1: HTML preprocessing
│   ├── fix_latex.py      # Step 3: LaTeX post-processing
│   ├── table_latex.py    # Table conversion (used by fix_latex)
│   ├── image_paths.py    # Resolve paths, AVIF → PNG
│   ├── image_sizes.py    # Preserve image dimensions from HTML
│   ├── properties.py     # Cover metadata table
│   ├── katex_latex.py    # KaTeX → LaTeX math fixes
│   ├── unicode_map.py    # Unicode symbol replacements
│   ├── cleanup.py        # Remove intermediate files
│   └── console.py        # Terminal UI (colors, progress)
├── tests/
├── docs/                 # MkDocs documentation (this site)
├── n2t.sh                # Optional shell wrapper
├── mkdocs.yml
└── pyproject.toml
```

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

## Module notes

### `clean_html.py`

```python
from notion2tex.clean_html import clean_html_for_pandoc
clean_html_for_pandoc("page.html", "page_clean.html")
```

### `fix_latex.py`

```python
from notion2tex.fix_latex import fix_latex
fix_latex("page.tex")
```

### Customization

| Goal | Where to change |
|------|------------------|
| TOC depth (section levels) | `fix_latex.py` → `_add_table_of_contents()` (`tocdepth`) |
| First numbered section marker | `fix_latex.py` → `_add_table_of_contents()` (`marker`) |
| Cover page title | `fix_latex.py` → `_unnumbered_cover_section()` |
| Toggle → heading depth cap | `clean_html.py` → `h_level = min(1 + nesting_depth, 6)` |
| Property tables (cover metadata) | `properties.py`, `table_latex.py` |

## Publishing to PyPI

1. Bump `__version__` in `notion2tex/__init__.py` (read by `pyproject.toml` via Hatch).
2. Tag the release (optional): `git tag v0.1.1 && git push origin v0.1.1`
3. Build and upload:

```bash
rm -rf dist/ build/
python -m build
twine check dist/*
twine upload dist/*
```

You cannot replace an existing version on PyPI; always use a new version number.

## Documentation site

Built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

Local preview:

```bash
pip install -r docs/requirements.txt
mkdocs serve
```

Production deploy: push to `main` — GitHub Actions publishes to GitHub Pages (see `.github/workflows/docs.yml`).

After the first deploy, enable **Settings → Pages → Source: GitHub Actions** on the repository if prompted.

Alternative: import the repo on [Read the Docs](https://readthedocs.org/) and point the build to `docs/requirements.txt` and `mkdocs.yml`.

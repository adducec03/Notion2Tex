# Development

## Contributing

Notion2Tex is open source under the [MIT license](https://github.com/adducec03/Notion2Tex/blob/main/LICENSE). Contributions are welcome from everyone — no prior approval needed.

1. Fork the [repository](https://github.com/adducec03/Notion2Tex) and clone it locally.
2. Create a branch for your change.
3. Install in editable mode and run the test suite (see below).
4. Open a [pull request](https://github.com/adducec03/Notion2Tex/pulls) with a short description of what you fixed or added.

Bug reports, export samples (redacted if needed), and documentation improvements are valuable too — use [GitHub Issues](https://github.com/adducec03/Notion2Tex/issues).

## Project structure

```
Notion2Tex/
├── notion2tex/           # Installable package
│   ├── cli.py            # Command-line interface
│   ├── pipeline.py       # Full build orchestration
│   ├── zip_export.py     # Extract Notion .zip, find main .html
│   ├── clean_html.py     # Step 1: HTML preprocessing
│   ├── remote_images.py  # Download images Notion only linked to
│   ├── fix_latex.py      # Step 3: LaTeX post-processing (incl. dark theme)
│   ├── table_latex.py    # Table conversion (used by fix_latex)
│   ├── image_paths.py    # Resolve paths, AVIF → PNG
│   ├── image_sizes.py    # Preserve image dimensions/alignment from HTML
│   ├── properties.py     # Strips the cover properties table
│   ├── katex_latex.py    # KaTeX → LaTeX math fixes
│   ├── unicode_map.py    # Unicode symbol replacements
│   ├── cleanup.py        # Remove intermediate files
│   ├── console.py        # Terminal UI (colors, progress)
│   └── filters/
│       └── notion_formatting.lua   # Pandoc Lua filter (see below)
├── tests/
├── docs/                 # MkDocs documentation (this site)
├── Dockerfile            # Containerized build (see DOCKER.md)
├── n2t.sh                # Optional shell wrapper
├── mkdocs.yml
└── pyproject.toml
```

### The Lua filter (`notion2tex/filters/notion_formatting.lua`)

Pandoc's LaTeX writer has no built-in handling for several Notion constructs (inline color/highlight, underline, multi-column layout, callouts, bookmark cards) — it keeps the information in its AST (visible via `pandoc -t native`) but silently drops it when writing LaTeX. The filter intercepts the relevant AST nodes (`Span`, `Div`, `Figure`, `BlockQuote`) and emits raw LaTeX (`\textcolor`, `\hl`, `minipage`, `tcolorbox`, `leftbar`) instead.

It reads a `NOTION2TEX_DARK` environment variable — set by `pipeline.py` when `--dark` is passed — to pick a color palette tuned for a dark background instead of Notion's own light-theme colors.

If you add a new Notion block type that needs special LaTeX handling, this filter is almost always the right place: it runs with full access to the Pandoc AST, and can call `pandoc.write()` to recursively render nested content (used by the column/callout/bookmark renderers).

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
| Cover page layout / title page | `fix_latex.py` → `_build_cover_page()` |
| Running chapter header | `fix_latex.py` → `_add_running_chapter_header()` |
| Toggle → heading depth cap | `clean_html.py` → `h_level = min(1 + nesting_depth, 6)` |
| Cover properties table (currently always removed) | `properties.py` |
| Colored/highlighted text, columns, callouts, quotes, bookmark cards | `filters/notion_formatting.lua` |
| Dark mode palette | `filters/notion_formatting.lua` (`DARK_TEXT_COLORS`, `DARK_BACKGROUND_COLORS`) and `fix_latex.py` (`_apply_dark_theme`, `_DARK_*` constants) |
| Remote image download timeout/behavior | `remote_images.py` |

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

### Enable GitHub Pages (required once)

If the workflow fails with `Failed to create deployment (status: 404)`:

1. Open [Settings → Pages](https://github.com/adducec03/Notion2Tex/settings/pages) on the repository.
2. Under **Build and deployment**, set **Source** to **GitHub Actions** (not “Deploy from a branch”).
3. Re-run the workflow: **Actions → Deploy documentation → Re-run all jobs**.

The site will be at **https://adducec03.github.io/Notion2Tex/** after a successful deploy.

Alternative: import the repo on [Read the Docs](https://readthedocs.org/) and point the build to `docs/requirements.txt` and `mkdocs.yml`.

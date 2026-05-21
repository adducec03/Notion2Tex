# Notion2Tex

Convert a **Notion HTML export** into a printable **PDF** with correct heading hierarchy, math, tables, images, and a clickable table of contents.

Designed for large course notes exported from Notion with KaTeX formulas, nested toggles, and `simple-table` blocks.

All processing runs **on your machine** — nothing is uploaded.

## Quick start

```bash
pip install notion2tex
notion2tex --check
notion2tex "/path/to/Export.zip"
```

You also need [Pandoc](https://pandoc.org/installing.html) and [TeX Live](https://www.tug.org/texlive/) (or MacTeX) with `pdflatex`.

## Where to go next

| Guide | Contents |
|-------|----------|
| [Installation](installation.md) | PyPI, development setup, Pandoc and TeX |
| [Usage](usage.md) | ZIP vs HTML, CLI options, Notion export steps |
| [Pipeline](pipeline.md) | clean HTML → Pandoc → LaTeX fixes → PDF |
| [Development](development.md) | Package layout and module reference |
| [Troubleshooting](troubleshooting.md) | Common errors and fixes |

## Links

- [PyPI package](https://pypi.org/project/notion2tex/)
- [GitHub repository](https://github.com/adducec03/Notion2Tex)
- [Report an issue](https://github.com/adducec03/Notion2Tex/issues)

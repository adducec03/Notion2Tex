# Development

## Contributing

Notion2Tex is open source under the [MIT license](https://github.com/adducec03/Notion2Tex/blob/main/LICENSE) — contributions are welcome, no prior approval needed.

1. Fork the [repository](https://github.com/adducec03/Notion2Tex) and clone it.
2. Install in editable mode and run the tests (see below).
3. Open a [pull request](https://github.com/adducec03/Notion2Tex/pulls) describing what you changed.

Bug reports, export samples, and doc improvements are just as welcome — use [GitHub Issues](https://github.com/adducec03/Notion2Tex/issues).

## Project structure

```
Notion2Tex/
├── notion2tex/           # Installable package
│   ├── cli.py            # Command-line interface
│   ├── pipeline.py        # Build orchestration
│   ├── clean_html.py      # HTML preprocessing
│   ├── fix_latex.py       # LaTeX post-processing (incl. --book, --dark)
│   ├── remote_images.py   # Downloads linked images
│   └── filters/
│       └── notion_formatting.lua   # Pandoc Lua filter
├── tests/
├── docs/                 # This site
├── scripts/              # Docker wrapper scripts
├── Dockerfile
└── pyproject.toml
```

The Lua filter is where Notion-specific formatting (colors, columns, callouts, bookmark cards) gets translated into LaTeX that Pandoc's writer doesn't produce on its own. It's the first place to look if you're adding support for a new Notion block type.

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

## Releasing a new version

A single git tag publishes both PyPI and the Docker image, and both refuse to publish if they don't agree on the version number:

1. Bump `__version__` in `notion2tex/__init__.py`.
2. Commit it to `main`.
3. Tag and push: `git tag v0.2.0 && git push origin v0.2.0`.

That triggers two GitHub Actions workflows: `notion2tex==0.2.0` on PyPI, and `ghcr.io/adducec03/notion2tex:0.2.0` on GitHub Container Registry. See the workflow files for one-time setup notes (PyPI trusted publishing, package visibility).

## Documentation site

Built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

```bash
pip install -r docs/requirements.txt
mkdocs serve   # preview at http://127.0.0.1:8000
```

Pushing to `main` deploys it automatically to GitHub Pages.

# Pipeline

Notion2Tex runs four steps in order:

```mermaid
flowchart LR
  A[Notion export .zip] --> Z[Extract ZIP]
  Z --> B[clean_html]
  B --> C["*_clean.html"]
  C --> D[Pandoc]
  D --> E["*.tex"]
  E --> F[fix_latex]
  F --> G[table_latex]
  G --> H["*.tex fixed"]
  H --> I[pdflatex x2]
  I --> J["*.pdf"]
```

## 1. Extract ZIP (`zip_export.py`)

Unpacks the Notion `.zip`, finds the main `.html` page, and resolves paths relative to the export folder.

## 2. Clean HTML (`clean_html.py`)

Prepares Notion HTML before Pandoc:

| Step | What it does |
|------|----------------|
| Toggles → headings | Nested `<details>` become `<h1>`–`<h6>` (deepest first) |
| Toggle lists | Flattens spurious list markup before paragraph toggles |
| Table repair | Removes invalid `<div>` wrappers inside `<table>` |
| Properties | Normalizes the cover metadata table |
| Math | KaTeX `<annotation>` → MathML (inline) or `$$...$$` (display) |
| SVG removal | Drops SVG icons/images that break `pdflatex` |
| Emoji removal | Strips emoji characters |

## 3. Pandoc

Converts cleaned HTML to a standalone LaTeX document. Invoked as a subprocess with paths relative to the HTML file so images resolve correctly.

## 4. Fix LaTeX (`fix_latex.py`, `table_latex.py`)

Post-processes the `.tex` file:

| Area | Fix |
|------|-----|
| Structure | Section numbering `1.` / `1.1.` / `1.1.1.`; unnumbered cover page |
| TOC | `\tableofcontents` after cover; roman numerals for front matter, arabic from page 1 for body |
| Figures | `[H]` placement; image path fixes; AVIF → PNG on macOS via `sips` |
| Math | Escaped `\$...\$`, `\textbackslash`, `gather*` / `cases`, Unicode symbols |
| Titles | Corrupted `\section{...}` with KaTeX / bookmarks |
| Captions | Removes empty `\caption{}` / spurious “Figure N” |
| Tables | Rebuilds `longtable` → `tabular` / `tabularx` with `booktabs` |
| Strikeout | `soul` → `ulem` → no-op if packages missing |

## 5. Build PDF (`pdflatex`)

Runs `pdflatex` twice so the table of contents and page numbers are correct. Intermediate LaTeX artifacts are cleaned up after success (`cleanup.py`).

## Entry points

- **CLI:** `notion2tex` → `notion2tex.cli:main`
- **Python:** `notion2tex.pipeline.convert()`

# How it works

Notion2Tex turns a Notion export into a PDF in five steps:

```mermaid
flowchart LR
  A[Notion export .zip] --> Z[Extract ZIP]
  Z --> B[Clean HTML]
  B --> D[Pandoc + Lua filter]
  D --> F[Fix LaTeX]
  F --> I[pdflatex]
  I --> J["Final PDF"]
```

## 1. Extract the ZIP

Unpacks the export and locates the main HTML page and its asset folder.

## 2. Clean the HTML

Notion's export format needs some preparation before Pandoc can read it correctly: nested toggles become proper headings, tables and math formulas get repaired, images (including page covers and other Notion-hosted links) get resolved or downloaded locally, and elements that would break `pdflatex` (like SVG icons) are removed.

## 3. Convert with Pandoc

Pandoc turns the cleaned HTML into LaTeX. A bundled Lua filter fills in the formatting Pandoc doesn't handle out of the box — colored/highlighted text, underline, multi-column layouts, callout boxes, quotes, and web-bookmark cards — so it matches what you see in Notion.

## 4. Fix up the LaTeX

The raw LaTeX from Pandoc gets polished: tables rebuilt for correct alignment, image paths and sizes fixed, math edge cases corrected — including long formulas and long code lines that would otherwise run off the page, which are shrunk and wrapped to fit — and (in `--dark` mode) a full dark color scheme applied. With `--book`, this step also adds a designed title page, a table of contents, a page break before each top-level section, and a running chapter header.

## 5. Build the PDF

`pdflatex` runs twice, so cross-references and page numbers (and the table of contents, in `--book` mode) come out correct. Intermediate files are removed once the PDF is built successfully.

## Want more detail?

The [Development](development.md) page covers the project's internal structure, if you want to read or modify the code.

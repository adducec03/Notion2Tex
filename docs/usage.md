# Usage

## Export from Notion

1. Open the page in Notion and export it as **HTML** — Notion gives you a `.zip` file.
2. Run Notion2Tex on that ZIP.
3. Don't rename or move files inside the export before converting; the HTML refers to them by relative path.

## Convert

```bash
notion2tex "/path/to/Export.zip"
```

Notion2Tex extracts the ZIP, cleans up the HTML, and builds a PDF next to it. If you've already extracted the export yourself, point it at the `.html` file instead:

```bash
notion2tex "/path/to/export/Page Name.html"
```

## Output

For a page `Automata.html`, you'll get:

| File | What it is |
|------|-------------|
| `Automata.pdf` | The final PDF |
| `Automata.tex` | The generated LaTeX source |
| `Automata.log` | pdflatex's build log |

Intermediate files are cleaned up automatically after a successful run.

## Useful flags

```bash
notion2tex --check                    # verify Pandoc + pdflatex are installed
notion2tex Export.zip --dark          # dark-mode PDF
notion2tex Export.zip --tex-only      # generate the .tex without building a PDF
notion2tex Export.zip -v              # show full compiler output
notion2tex --help                     # everything else
```

## What carries over from Notion

Colors, highlights, underline, strikethrough, multi-column layouts, callouts, quotes, syntax-highlighted code, image alignment, and page covers are all preserved in the PDF — not flattened to plain text. See [Troubleshooting](troubleshooting.md) if something looks off.

### Dark mode

`--dark` produces a dark gray page with light text and adjusted colors, instead of just inverting Notion's light-theme palette (which would look washed out):

```bash
notion2tex Export.zip --dark
```

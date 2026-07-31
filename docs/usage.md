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

Intermediate files are cleaned up automatically after a successful run. Want the PDF somewhere else? See `--output` below.

## Useful flags

```bash
notion2tex --check                    # verify Pandoc + pdflatex are installed
notion2tex Export.zip --book          # add book-style structure (see below)
notion2tex Export.zip --lang it       # translated headings + hyphenation
notion2tex Export.zip --dark          # dark-mode PDF
notion2tex Export.zip --offline       # no network calls at all (see below)
notion2tex Export.zip --output ~/Notes.pdf   # custom output path (see below)
notion2tex Export.zip --tex-only      # generate the .tex without building a PDF
notion2tex Export.zip -v              # show full compiler output
notion2tex --help                     # everything else
```

## What carries over from Notion

Colors, highlights, underline, strikethrough, multi-column layouts, callouts, quotes, syntax-highlighted code, image alignment, and page covers are all preserved in the PDF — not flattened to plain text. See [Troubleshooting](troubleshooting.md) if something looks off.

### Book mode

By default, the PDF flows continuously — no title page, no table of contents, no forced page breaks. That fits a single note or a short page well. For something longer (course notes, a multi-chapter document), add `--book`:

```bash
notion2tex Export.zip --book
```

This adds a designed cover page (using the page's own cover image and title), a table of contents, a page break before every top-level section, and a running header showing the current section name.

### Language

By default, generated headings (like the table of contents, in `--book` mode) use plain English, and hyphenation follows whatever your TeX install defaults to. Pass `--lang {en,it}` to load the matching hyphenation rules and translate those headings — most noticeable combined with `--book`:

```bash
notion2tex Export.zip --lang it
notion2tex Export.zip --book --lang it
```

### Dark mode

`--dark` produces a dark gray page with light text and adjusted colors, instead of just inverting Notion's light-theme palette (which would look washed out). Combine freely with `--book` and `--lang`:

```bash
notion2tex Export.zip --dark
notion2tex Export.zip --book --lang it --dark
```

### Offline mode

Notion2Tex normally makes one kind of outbound request: downloading images Notion itself only linked to rather than embedded (page covers, "image from link" blocks, bookmark previews). `--offline` skips that entirely — no network calls at all — at the cost of those specific images being omitted from the PDF:

```bash
notion2tex Export.zip --offline
```

### Custom output path

By default the PDF is written next to the input file. `--output` moves the finished PDF (or `.tex`, with `--tex-only`) to a path of your choice instead — parent directories are created automatically. The `.tex`/`.log` build files still stay in the export folder (pdflatex needs to run there for image paths to resolve):

```bash
notion2tex Export.zip --output ~/Documents/Notes.pdf
```

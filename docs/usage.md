# Usage

## Export from Notion

1. Open the Notion page (or run a workspace export).
2. Export as **HTML** (include subpages if you need them). Notion delivers a **`.zip`** file.
3. Run Notion2Tex on that ZIP. The tool extracts the archive and keeps image paths intact (`Page.html` + `Page/` asset folder).
4. Do not rename or move files inside the export before converting; paths in the HTML are relative to the `.html` file.

!!! note "Database properties"
    The cover/properties table shows **every field present in the HTML export**. Notion often omits **Password**-type properties from HTML exports. If a field is missing from the PDF, open the raw `.html` in a browser or editor and confirm the row exists before converting.

## Convert a ZIP (recommended)

```bash
notion2tex "/path/to/Export.zip"
```

The ZIP is extracted to a folder with the same name (e.g. `Export.zip` → `Export/`), then the pipeline runs on the main page inside it.

## Convert a single HTML file

If the export is already extracted:

```bash
notion2tex "/path/to/export/Page Name.html"
```

The `.html` must sit next to its asset folder (same layout as Notion’s export).

## Output files

For a page `Automata.html` inside `Export/`:

| File | Description |
|------|-------------|
| `Automata.html` | Original Notion export (unchanged) |
| `Automata.tex` | LaTeX source |
| `Automata.pdf` | Final PDF |
| `Automata.log` | pdflatex log (when PDF is built) |

Intermediate files (`_clean.html`, `.aux`, `.toc`, `.out`, …) are removed automatically after a successful run.

Files are written **next to the HTML** inside the export folder.

## CLI options

```bash
notion2tex --help
notion2tex --check                    # verify pandoc + pdflatex
notion2tex --version
notion2tex Export.zip --tex-only      # LaTeX only, no pdflatex
notion2tex Export.zip -v              # show compiler output
notion2tex Export.zip --no-color      # plain terminal output
notion2tex Export.zip --extract-dir ./work
```

## Manual build (LaTeX only)

Generate `.tex` without running `pdflatex`:

```bash
notion2tex automata.html --tex-only
cd "$(dirname automata.html)"
rm -f automata.aux automata.toc automata.out
pdflatex -interaction=nonstopmode automata.tex
pdflatex -interaction=nonstopmode automata.tex
```

The second `pdflatex` pass is **required** for a correct table of contents and page numbers.

Or run the full pipeline in one step:

```bash
notion2tex automata.html
```

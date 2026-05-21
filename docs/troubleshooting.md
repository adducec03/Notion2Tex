# Troubleshooting

## `Missing \begin{document}` with hex garbage in `.aux`

The auxiliary file is corrupted (often after interrupting `pdflatex`):

```bash
rm -f page.aux page.toc page.out
pdflatex -interaction=nonstopmode page.tex
pdflatex -interaction=nonstopmode page.tex
```

Or re-run the full pipeline: `notion2tex page.html`.

## `Package array Error` near `\end{tabularx}`

Usually a malformed table column spec from an older build. Re-run the full pipeline so `table_latex.py` regenerates tables.

## Tables appear as separate text blocks (not columns)

The source HTML still has Notion `<div>` inside `<tbody>`. Re-run the pipeline from the original export ZIP so `clean_html.py` can repair tables.

## Course properties table missing fields

Notion2Tex shows **every property row present in the HTML export**. During cleaning, the log lists field names found, for example:

`Normalized properties table (4 fields): Sito web, Username, Password, Status`

If username/password are missing from that list, they are **not in the export file**. Notion often omits **Password**-type database properties from HTML exports. Use **Text** properties, re-export, and confirm the fields appear in the raw `.html` before converting.

## Empty or wrong table of contents

Run `pdflatex` **twice**. Delete `.toc` / `.aux` first if you changed section structure, or run `notion2tex` again on a fresh export.

## Missing images in PDF

- Keep image folders from the Notion export **next to the HTML** with the same relative paths as in the export.
- Do not rename the asset folder or move images before converting.
- On macOS, AVIF images are converted to PNG via `sips` when needed.

## `File ...sty not found`

Install a full TeX distribution (TeX Live / MacTeX). Common packages:

```bash
tlmgr install soul ulem float booktabs tabularx hyperref
```

Notion2Tex falls back when `soul` is missing; some Pandoc outputs still need `float`, `booktabs`, or `tabularx`.

## `Missing tools: pandoc` or `pdflatex`

Run `notion2tex --check`. Install Pandoc and TeX Live, ensure both are on your `PATH` in the same shell where you run `notion2tex`.

## Spurious `\item ~` before toggle titles

Fixed in current releases by flattening toggle lists in `clean_html.py` and unwrapping paragraph itemize in `fix_latex.py`. Upgrade with `pip install -U notion2tex`.

## Get help

- [GitHub Issues](https://github.com/adducec03/Notion2Tex/issues)
- Include the `notion2tex` version (`notion2tex --version`), OS, and relevant lines from the `.log` file

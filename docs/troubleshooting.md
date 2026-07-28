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
tlmgr install soul ulem float booktabs tabularx hyperref tcolorbox framed lmodern
```

Notion2Tex falls back when `soul`/`ulem` are missing (strikethrough/underline become plain text); `tcolorbox` and `framed` are required for callouts, quotes, and bookmark cards and have no fallback. On Debian/Ubuntu, `soul`/`ulem` ship in `texlive-plain-generic`, not `texlive-latex-extra` — see [Installation](installation.md).

## Colored text, highlights, underline, columns, or callouts are missing/plain in the PDF

Almost always an **old Pandoc**. Pandoc's writer has no built-in support for these — Notion2Tex re-injects them via a bundled Lua filter, but only a fairly recent Pandoc build runs it correctly. Check:

```bash
pandoc --version
```

If it's more than a year or two old (common with `apt install pandoc` on Debian/Ubuntu), install a current release from [pandoc.org](https://pandoc.org/installing.html), or use the Docker image, which pins a known-good version.

## Code blocks are not syntax-highlighted

Pandoc only colors a code block when the `<code>` tag's class is the bare language name (`python`, not `language-python`) **and** the wrapping `<pre>` has no class or data attributes of its own — Notion's export has both, so this is fixed automatically in `clean_html.py`. If it's still plain after upgrading, check that the language Notion assigned is one Pandoc recognizes (`pandoc --list-highlight-languages`); an unrecognized language silently renders as plain text (no error).

## Linked/external images are missing or show a broken box with a URL

Page covers, "image from link" blocks, and web-bookmark previews are not embedded in the export — Notion only stores a URL. Notion2Tex downloads them during conversion (look for `Remote images downloaded → N` in the log) and stores them in a `notion2tex_downloads/` folder next to the HTML. If a download fails (network unavailable, broken URL, non-image response), that one image is omitted cleanly rather than breaking the build — check the log for `Could not download image, omitting: <url>` and verify the URL still resolves in a browser.

## `--dark` output has low-contrast or invisible text somewhere

If a specific block still shows dark text on the dark page, it's most likely a construct not yet covered by the dark-mode color fixes (LaTeX floats, boxes, and headers/footers are typeset separately from the main text and don't automatically inherit the page's text color — see [Pipeline](pipeline.md)). Report it on [GitHub Issues](https://github.com/adducec03/Notion2Tex/issues) with the block type (table, callout, quote, etc.) so it can be added.

## `Missing tools: pandoc` or `pdflatex`

Run `notion2tex --check`. Install Pandoc and TeX Live, ensure both are on your `PATH` in the same shell where you run `notion2tex`.

## Spurious `\item ~` before toggle titles

Fixed in current releases by flattening toggle lists in `clean_html.py` and unwrapping paragraph itemize in `fix_latex.py`. Upgrade with `pip install -U notion2tex`.

## Get help

- [GitHub Issues](https://github.com/adducec03/Notion2Tex/issues)
- Include the `notion2tex` version (`notion2tex --version`), OS, and relevant lines from the `.log` file

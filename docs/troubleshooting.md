# Troubleshooting

## `Missing \begin{document}` or other corrupted-looking LaTeX errors

Usually a leftover `.aux`/`.toc`/`.out` file from an interrupted build. Delete them and rebuild:

```bash
rm -f page.aux page.toc page.out
notion2tex page.html
```

## Tables look broken, or appear as separate text blocks instead of a table

Re-run the conversion from the original export ZIP (not an already-extracted copy) so the table-repair step can do its job.

## Missing images in the PDF

- Keep the image folder next to the HTML file, with the same name and layout as in the original export.
- AVIF/WebP images need converting to PNG first — this happens automatically via `sips` (macOS) or `avifdec`/`dwebp` (Linux, included in the provided Docker image). Without one of these tools, that image is skipped rather than breaking the build.

## Linked or external images (page covers, bookmark previews) are missing

These aren't embedded in the export — Notion only stores a URL, and Notion2Tex downloads them during conversion. Check the log for `Could not download image, omitting: <url>` and confirm the URL still works in a browser.

Running in Docker: this needs `ca-certificates` available at runtime, not just during the image build. The official image already includes it.

## `File ...sty not found`

Install a full TeX distribution and the packages it's missing, for example:

```bash
tlmgr install soul ulem float booktabs tabularx hyperref tcolorbox framed lmodern
```

On Debian/Ubuntu, `soul`/`ulem` come from `texlive-plain-generic`, not `texlive-latex-extra`.

## Colors, highlights, underline, columns, or callouts are missing or plain in the PDF

Almost always an outdated Pandoc. Check with `pandoc --version` — if it's more than a year or two old (common with `apt install pandoc`), install a current release from [pandoc.org](https://pandoc.org/installing.html), or use the [Docker image](installation.md#option-1-docker-recommended), which always has a known-good version.

## Code blocks aren't syntax-highlighted

Make sure the language Notion assigned is one Pandoc recognizes (`pandoc --list-highlight-languages`). An unrecognized language renders as plain text without an error.

## `--dark` output has low-contrast or invisible text somewhere

If a specific block still looks dark-on-dark, it's likely a construct not yet covered by the dark-mode styling. [Open an issue](https://github.com/adducec03/Notion2Tex/issues) with the block type (table, callout, quote, etc.).

## The cover properties table (site, username, password...) isn't in the PDF

That's intentional — it's page metadata, not content meant to be printed.

## `Missing tools: pandoc` or `pdflatex`

Run `notion2tex --check` to confirm what's missing, then see [Installation](installation.md).

## Get help

- [GitHub Issues](https://github.com/adducec03/Notion2Tex/issues)
- Include your Notion2Tex version (`notion2tex --version`), OS, and the relevant lines from the `.log` file.

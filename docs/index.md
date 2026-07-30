<div class="n2t-landing" markdown="1">

<p class="n2t-eyebrow">Notion2Tex</p>

# Turn Notion exports into print-ready PDFs

Course notes, wikis, and long-form pages — with math, nested toggles, tables, images, colored text, and callouts — become a single **PDF** you can read offline or send to print.

Notion2Tex is a small command-line tool that fixes what generic converters miss, then builds the document with **Pandoc** and **LaTeX** on your computer.

[Install](installation.md){ .md-button .md-button--primary }
[How it works](pipeline.md){ .md-button }

</div>

<div class="n2t-privacy" markdown="1">

## Your notes never leave your machine

Notion2Tex does not use cloud APIs, accounts, or upload steps. You export HTML from Notion, run the tool locally, and get a PDF next to your files.

- **Nothing is uploaded** — conversion runs entirely on your machine with your shell, Pandoc, and `pdflatex`
- **The only outbound requests** are to download images Notion itself only linked to (page covers, "image from link" blocks, bookmark previews) — never your page content
- **No telemetry** or analytics in the CLI
- **You keep the source** — the original HTML export stays untouched; outputs are `.tex`, `.pdf`, and optional `.log`

Your content stays on your disk, under your control.

</div>

<div class="n2t-features" markdown="1">

## Built for real Notion exports

<div class="n2t-feature-grid" markdown="1">

<div class="n2t-feature" markdown="1">

**Structure**

Nested toggles become a proper heading hierarchy, with a matching table of contents.

</div>

<div class="n2t-feature" markdown="1">

**Math & tables**

Formulas and tables come through correctly, not as broken text or images.

</div>

<div class="n2t-feature" markdown="1">

**Images & cover**

Sizes, alignment, and page covers carry over as set in Notion — including images Notion only links to.

</div>

<div class="n2t-feature" markdown="1">

**Formatting & dark mode**

Colors, highlights, underline, columns, callouts, and syntax-highlighted code all carry over. Add `--dark` for a dark PDF.

</div>

</div>

</div>

<div class="n2t-flow" markdown="1">

## How it works

<ol class="n2t-steps">
<li><strong>Export</strong> — Save the page from Notion as HTML (ZIP).</li>
<li><strong>Convert</strong> — <code>notion2tex Export.zip</code> cleans HTML, runs Pandoc, post-processes LaTeX, builds the PDF.</li>
<li><strong>Done</strong> — Open the PDF beside your export. Intermediate files are removed after a successful run.</li>
</ol>

```bash
curl -O https://raw.githubusercontent.com/adducec03/Notion2Tex/main/scripts/notion2tex-docker.sh
chmod +x notion2tex-docker.sh
./notion2tex-docker.sh "/path/to/Export.zip"
```

No Pandoc or TeX to install — it's all bundled in the Docker image. Prefer `pip install notion2tex`? See [Installation](installation.md) for that and other options.

</div>

<div class="n2t-community" markdown="1">

## Open source — help it grow

Notion2Tex is **free and open source** ([MIT license](https://github.com/adducec03/Notion2Tex/blob/main/LICENSE)). The code lives on GitHub; anyone can use it, study it, and improve it.

Whether you fix a bug, improve Notion HTML handling, update the docs, or share feedback from a real export — **contributions are welcome**. You do not need permission to open an issue or propose a pull request.

[View on GitHub](https://github.com/adducec03/Notion2Tex){ .md-button .md-button--primary }
[Report an issue](https://github.com/adducec03/Notion2Tex/issues){ .md-button }
[Contributing guide](development.md){ .md-button }

</div>

<div class="n2t-footer-links" markdown="1">

[Installation guide](installation.md) · [Usage](usage.md) · [Troubleshooting](troubleshooting.md) · [GitHub](https://github.com/adducec03/Notion2Tex) · [PyPI](https://pypi.org/project/notion2tex/)

</div>

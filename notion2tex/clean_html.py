from bs4 import BeautifulSoup, NavigableString
import html
import os
import sys
from pathlib import Path
import emoji
import re

from notion2tex.console import console
from notion2tex.image_sizes import apply_notion_image_sizes
from notion2tex.katex_latex import normalize_katex
from notion2tex.properties import normalize_properties_table
from notion2tex.remote_images import download_remote_images

ZERO_WIDTH = ("\ufeff", "\u200b", "\u200c", "\u200d")


def _clean_text(text):
    for char in ZERO_WIDTH:
        text = text.replace(char, "")
    return text.strip()


_EQUATION_ATTRS = ("data-notion-equation", "data-notion-inline-equation")


def _latex_from_element(element):
    """
    LaTeX for an element that IS itself a Notion equation container/token.

    Current Notion exports store the raw LaTeX source directly on the
    container in a ``data-notion-equation`` / ``data-notion-inline-equation``
    attribute (checked on the element itself, not its subtree: a heading can
    mix plain text with a nested equation token, e.g. "Numerabilità di
    <equation>", and searching descendants would wrongly find the equation
    and collapse the whole heading to math, dropping the surrounding text).

    Older exports instead embed a KaTeX ``<annotation>`` somewhere inside the
    element's own rendering subtree; kept as a fallback for those.
    """
    for attr in _EQUATION_ATTRS:
        if element.has_attr(attr):
            return normalize_katex(_clean_text(element[attr]))

    ann = element.find("annotation", encoding="application/x-tex")
    if ann:
        return normalize_katex(_clean_text(ann.get_text()))
    return None


def _heading_parts(element):
    """
    Rebuild a heading as a list of (text | math) parts.
    Avoids duplicate text from katex-html
    """
    parts = []

    for child in element.children:
        if isinstance(child, NavigableString):
            text = _clean_text(str(child))
            if text:
                parts.append(("text", text))
        elif child.name in ("style", "script"):
            continue
        else:
            latex = _latex_from_element(child)
            if latex:
                parts.append(("math", latex))
            else:
                parts.extend(_heading_parts(child))

    return parts


def _mathml(latex, *, display_block=False):
    """
    Minimal MathML wrapping a KaTeX/LaTeX annotation.

    Pandoc's HTML reader turns this into real inline math (\\(...\\)) or,
    with ``display="block"``, real display math (\\[...\\]) — as opposed to
    inserting raw "$"/"$$" text, which Pandoc does not recognize as math
    delimiters and would instead escape as literal characters.

    The LaTeX is HTML-escaped: it is re-parsed as HTML immediately below
    (BeautifulSoup(...)), so a literal "<" or ">" in the formula (e.g. a
    tuple like <x_1,...,x_n> or a "<"/">" comparison) would otherwise be
    read as a tag and silently truncate the annotation.
    """
    attr = ' display="block"' if display_block else ""
    escaped = html.escape(latex, quote=False)
    return (
        f'<math xmlns="http://www.w3.org/1998/Math/MathML"{attr}>'
        "<semantics><mrow></mrow>"
        f'<annotation encoding="application/x-tex">{escaped}</annotation>'
        "</semantics></math>"
    )


def _inline_mathml(latex):
    return _mathml(latex)


def _build_heading(soup, level, parts):
    tag = soup.new_tag(f"h{level}")
    for kind, content in parts:
        if kind == "text":
            tag.append(content)
            tag.append(" ")
        elif kind == "math":
            tag.append(BeautifulSoup(_inline_mathml(content), "html.parser"))
    if tag.contents and isinstance(tag.contents[-1], NavigableString):
        last = tag.contents[-1]
        if str(last).endswith(" "):
            last.replace_with(str(last).rstrip())
    return tag


def _replace_block_equation(figure):
    """Replace a Notion equation figure (block math) with display MathML."""
    latex = _latex_from_element(figure)
    if not latex:
        return False
    if "\\\\" in latex:
        latex = f"\\begin{{gathered}}\n{latex}\n\\end{{gathered}}"
    mathml = BeautifulSoup(_mathml(latex, display_block=True), "html.parser")
    figure.replace_with(mathml)
    return True


def _replace_inline_equation(container):
    """Replace a Notion inline equation token/span with inline MathML."""
    latex = _latex_from_element(container)
    if not latex:
        return False
    mathml = BeautifulSoup(_inline_mathml(latex), "html.parser")
    container.replace_with(mathml)
    return True


def _repair_notion_tables(soup):
    """
    Notion wraps rows in <div> inside <tbody>/<tr>: invalid HTML and Pandoc
    splits tables into separate LTR blocks instead of longtable/tabular.
    """
    count = 0
    for table in soup.find_all("table"):
        count += 1
        for tag in table.find_all(["tbody", "thead", "tr", "td", "th"]):
            for child in list(tag.children):
                if getattr(child, "name", None) == "div":
                    child.unwrap()
        for mark in table.find_all("mark"):
            mark.unwrap()
        for style in table.find_all("style"):
            style.decompose()
    return count


def _rename_callout_asides(soup):
    """
    Notion emits callouts as <aside class="...callout" data-notion-callout-*>.
    Pandoc's HTML reader drops <aside> wrappers entirely (unwrapping to their
    children), discarding the callout's classes/attributes with it. Renaming
    to <div> makes it keep them as a Div, which the pandoc Lua filter later
    turns into a colored tcolorbox.

    The icon attribute is an emoji; pdfLaTeX has no color-emoji glyphs (same
    reason emojis are stripped from body text elsewhere), so strip it here
    too rather than leave a raw codepoint pdflatex cannot typeset.
    """
    count = 0
    for aside in soup.find_all("aside"):
        icon = aside.get("data-notion-callout-icon")
        if icon:
            aside["data-notion-callout-icon"] = emoji.replace_emoji(icon, replace="")
        aside.name = "div"
        count += 1
    return count


def _fix_code_block_language(soup):
    """
    Notion marks a code block's language as <code class="language-python">.
    Pandoc's HTML reader only applies syntax highlighting when the class is
    the bare language name (e.g. "python"); with the "language-" prefix left
    on, it doesn't recognize it and silently renders everything in plain,
    uncolored text.

    The wrapping <pre class="code code-wrap" data-notion-code-syntax="...">
    also has to be stripped down to a bare <pre>: pandoc drops syntax
    highlighting entirely (falling back to a plain \\begin{verbatim}) the
    moment the <pre> itself carries any class or data attribute, regardless
    of the <code> child's language class.
    """
    count = 0
    for code in soup.find_all("code", class_=lambda c: c and "language-" in c):
        classes = code.get("class", [])
        code["class"] = [
            cl[len("language-") :] if cl.startswith("language-") else cl
            for cl in classes
        ]
        pre = code.find_parent("pre")
        if pre is not None:
            pre.attrs = {}
        count += 1
    return count


def _unwrap_toggle_lists(soup):
    """
    Notion toggle blocks use <ul class="toggle"><li><details>…</details></li></ul>.
    After converting details to headings, unwrap the list so Pandoc does not emit
    \\item ~ before \\paragraph{}.
    """
    count = 0
    for ul in list(soup.find_all("ul", class_=lambda c: c and "toggle" in c)):
        for li in list(ul.find_all("li", recursive=False)):
            li.unwrap()
        ul.unwrap()
        count += 1
    return count


def clean_html_for_pandoc(file_input, file_output):
    try:
        with open(file_input, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
    except FileNotFoundError:
        console.error(f"HTML not found: {file_input}")
        return

    work_dir = Path(file_input).resolve().parent
    bar = console.progress(10, "Preprocessing HTML")

    # 1. Nested toggles → h1–h6 (before body math; headings still have KaTeX annotations)
    toggles_found = 0
    headings_with_math = 0
    all_details = soup.find_all("details")
    all_details.sort(key=lambda d: len(d.find_parents("details")), reverse=True)

    for details in all_details:
        nesting_depth = len(details.find_parents("details"))
        h_level = min(1 + nesting_depth, 6)

        summary = details.find("summary")
        if summary:
            parts = _heading_parts(summary)
            new_heading = _build_heading(soup, h_level, parts)
            if any(kind == "math" for kind, _ in parts):
                headings_with_math += 1
            summary.replace_with(new_heading)
            toggles_found += 1

    for details in all_details:
        details.unwrap()
    toggles_unwrapped = _unwrap_toggle_lists(soup)
    bar.advance(sublabel="Toggles")
    console.detail(
        f"Toggles → {toggles_found} headings ({headings_with_math} with math), "
        f"{toggles_unwrapped} lists flattened"
    )

    # 2. Callouts: <aside> -> <div> so Pandoc keeps its classes/attributes
    callouts_renamed = _rename_callout_asides(soup)
    bar.advance(sublabel="Callouts")
    if callouts_renamed:
        console.detail(f"Callouts preserved → {callouts_renamed}")

    # 3. Code blocks: language-X -> X so Pandoc applies syntax highlighting
    code_blocks_fixed = _fix_code_block_language(soup)
    bar.advance(sublabel="Code blocks")
    if code_blocks_fixed:
        console.detail(f"Code block languages fixed → {code_blocks_fixed}")

    # 4. Remove the cover properties table (site/username/password/... —
    # not meant to appear in the generated PDF)
    prop_rows, prop_labels = normalize_properties_table(soup)
    bar.advance(sublabel="Properties")
    if prop_rows:
        console.detail(
            f"Properties table removed → {prop_rows} fields ({', '.join(prop_labels)})"
        )

    # 5. Repair Notion tables (before replacing math inside cells)
    tables_repaired = _repair_notion_tables(soup)
    bar.advance(sublabel="Tables")
    console.detail(f"Tables repaired → {tables_repaired}")

    # 6. Preserve Notion image widths (style="width: Npx")
    images_sized = apply_notion_image_sizes(soup)
    bar.advance(sublabel="Images")
    console.detail(f"Image widths preserved → {images_sized}")

    # 7. Download externally-hosted images (page cover, "image from link",
    # bookmark previews) so pdflatex can embed them like local assets
    images_downloaded = download_remote_images(soup, work_dir)
    bar.advance(sublabel="Remote images")
    if images_downloaded:
        console.detail(f"Remote images downloaded → {images_downloaded}")

    # 8. Restore math (block equation figures + inline Notion tokens)
    block_figures = soup.find_all("figure", class_=lambda c: c and "equation" in c)
    inline_tokens = soup.find_all("span", class_=lambda c: c and "equation" in c)
    formulas_found = 0
    total = len(block_figures) + len(inline_tokens)
    math_bar = console.progress(max(1, total), "Math formulas")
    for figure in block_figures:
        if _replace_block_equation(figure):
            formulas_found += 1
        math_bar.advance()
    for token in inline_tokens:
        if _replace_inline_equation(token):
            formulas_found += 1
        math_bar.advance()
    math_bar.finish(f"Math formulas ({formulas_found} restored)")
    bar.advance(sublabel="Math")
    console.detail(f"Math formulas restored → {formulas_found}")

    # 9. Remove SVG icons/images (break pdflatex)
    svgs_removed = 0
    for img in soup.find_all("img"):
        if ".svg" in img.get("src", "").lower():
            img.decompose()
            svgs_removed += 1

    for svg in soup.find_all("svg"):
        svg.decompose()
        svgs_removed += 1
    bar.advance(sublabel="SVG cleanup")
    if svgs_removed:
        console.detail(f"SVG elements removed → {svgs_removed}")

    # 10. Remove emojis
    for text_node in soup.find_all(string=True):
        cleaned = emoji.replace_emoji(text_node, replace="")
        if text_node != cleaned:
            text_node.replace_with(cleaned)

    with open(file_output, "w", encoding="utf-8") as f:
        f.write(str(soup))
    out = Path(file_output)
    bar.finish("Writing output")
    console.detail(f"Wrote {out.name}")


if __name__ == "__main__":
    source = "Export.html"
    destination = "Export_clean.html"

    if len(sys.argv) > 1:
        source = sys.argv[1]
        base, ext = os.path.splitext(source)
        destination = f"{base}_clean{ext}"

    clean_html_for_pandoc(source, destination)

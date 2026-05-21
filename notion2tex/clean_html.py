from bs4 import BeautifulSoup, NavigableString
import sys
import os
import emoji
import re

from notion2tex.katex_latex import normalize_katex

ZERO_WIDTH = ("\ufeff", "\u200b", "\u200c", "\u200d")


def _clean_text(text):
    for char in ZERO_WIDTH:
        text = text.replace(char, "")
    return text.strip()


def _latex_from_element(element):
    """Extract LaTeX from the first KaTeX annotation in the subtree."""
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


def _inline_mathml(latex):
    """Minimal MathML so Pandoc converts titles to \\texorpdfstring{...}{...}."""
    return (
        '<math xmlns="http://www.w3.org/1998/Math/MathML">'
        "<semantics><mrow></mrow>"
        f'<annotation encoding="application/x-tex">{latex}</annotation>'
        "</semantics></math>"
    )


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


def _replace_formula(annotation):
    latex = normalize_katex(_clean_text(annotation.get_text()))

    block_container = annotation.find_parent("figure", class_="block-equation")
    inline_container = annotation.find_parent("span", class_="equation")
    notion_token = annotation.find_parent(class_="notion-text-equation-token")

    if block_container:
        if "\\\\" in latex:
            block_container.replace_with(
                f"$$ \\begin{{gathered}}\n{latex}\n\\end{{gathered}} $$"
            )
        else:
            block_container.replace_with(f"$$ {latex} $$")
        return True
    mathml = BeautifulSoup(_inline_mathml(latex), "html.parser")
    if inline_container:
        inline_container.replace_with(mathml)
        return True
    if notion_token:
        notion_token.replace_with(mathml)
        return True
    return False


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


def clean_html_for_pandoc(file_input, file_output):
    print(f"Reading {file_input}...")
    try:
        with open(file_input, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
    except FileNotFoundError:
        print(f"Error: file not found: '{file_input}'")
        return

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
    print(
        f"Converted {toggles_found} toggles to headings "
        f"({headings_with_math} with math)."
    )

    # 2. Repair Notion tables (before replacing math inside cells)
    tables_repaired = _repair_notion_tables(soup)
    print(f"Repaired {tables_repaired} Notion tables.")

    # 3. Restore math (body + inline Notion tokens)
    formulas_found = 0
    for annotation in soup.find_all("annotation", encoding="application/x-tex"):
        if _replace_formula(annotation):
            formulas_found += 1
    print(f"Restored {formulas_found} math formulas.")

    # 4. Remove SVG icons/images (break pdflatex)
    svgs_removed = 0
    for img in soup.find_all("img"):
        if ".svg" in img.get("src", "").lower():
            img.decompose()
            svgs_removed += 1

    for svg in soup.find_all("svg"):
        svg.decompose()
        svgs_removed += 1
    print(f"Removed {svgs_removed} SVG elements.")

    # 5. Remove emojis
    for text_node in soup.find_all(string=True):
        cleaned = emoji.replace_emoji(text_node, replace="")
        if text_node != cleaned:
            text_node.replace_with(cleaned)
    print("Emoji removal complete.")

    with open(file_output, "w", encoding="utf-8") as f:
        f.write(str(soup))
    print(f"Success! Saved as: {file_output}")


if __name__ == "__main__":
    source = "Export.html"
    destination = "Export_clean.html"

    if len(sys.argv) > 1:
        source = sys.argv[1]
        base, ext = os.path.splitext(source)
        destination = f"{base}_clean{ext}"

    clean_html_for_pandoc(source, destination)

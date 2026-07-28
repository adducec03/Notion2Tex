import re
import sys
from pathlib import Path

from notion2tex.table_latex import improve_tables_in_document
from notion2tex.image_paths import fix_includegraphics_paths
from notion2tex.image_sizes import (
    apply_widths_to_includegraphics,
    center_figure_images,
    load_image_width_map,
    neutralize_pandocbounded_scale,
    unwrap_href_includegraphics,
)
from notion2tex.katex_latex import normalize_katex_in_document
from notion2tex.unicode_map import (
    UNICODE_TEXT,
    has_unicode_preamble,
    latex_for_codepoint,
    separate_glued_command_letters,
    unicode_preamble_lines,
)


def _unwrap_paragraph_itemize(text: str) -> tuple[str, int]:
    """
    Remove itemize wrappers that only hold ``\\item ~`` + ``\\paragraph{}`` (Notion toggles).
    """
    count = 0
    pattern = re.compile(
        r"\s*\\begin\{itemize\}\s*\n(?:\\tightlist\s*\n)?\s*\\item\s*~\s*\n",
    )
    while True:
        m = pattern.search(text)
        if not m:
            break
        body_start = m.end()
        depth = 1
        pos = body_start
        end_pos = None
        while pos < len(text) and depth > 0:
            next_begin = text.find(r"\begin{itemize}", pos)
            next_end = text.find(r"\end{itemize}", pos)
            if next_end == -1:
                break
            if next_begin != -1 and next_begin < next_end:
                depth += 1
                pos = next_begin + len(r"\begin{itemize}")
            else:
                depth -= 1
                if depth == 0:
                    end_pos = next_end
                    break
                pos = next_end + len(r"\end{itemize}")
        if end_pos is None:
            break
        text = text[: m.start()] + text[body_start:end_pos] + text[end_pos + len(r"\end{itemize}") :]
        if text[end_pos + len(r"\end{itemize}") :].startswith("\n"):
            text = text[: end_pos + len(r"\end{itemize}")] + text[
                end_pos + len(r"\end{itemize}") + 1 :
            ]
        count += 1
    return text, count


def _enable_section_numbering(text):
    """Enable 1 / 1.1 / 1.1.1 numbering for section/subsection/subsubsection."""
    text = re.sub(
        r"\\setcounter\{secnumdepth\}\{[^}]+\}\s*%[^\n]*",
        r"\\setcounter{secnumdepth}{3} % number through subsubsection",
        text,
        count=1,
    )
    numbering = r"""
\renewcommand{\thesection}{\arabic{section}.}
\renewcommand{\thesubsection}{\thesection\arabic{subsection}.}
\renewcommand{\thesubsubsection}{\thesubsection\arabic{subsubsection}.}
"""
    if r"\renewcommand{\thesection}" not in text:
        text = text.replace(r"\begin{document}", numbering + r"\begin{document}")
    return text


def _fix_figure_placement(text):
    """
    Pandoc uses floating figures (htbp); LaTeX moves them away from source order.
    [H] keeps images in document order.
    """
    text = text.replace(
        r"\usepackage{cancel}\n\\usepackage{float}",
        "\\usepackage{cancel}\n\\usepackage{float}",
    )
    if r"\usepackage{float}" not in text:
        for anchor in (
            r"\usepackage{grffile}",
            r"\usepackage{graphicx}",
            r"\usepackage{bookmark}",
        ):
            if anchor in text:
                text = text.replace(
                    anchor,
                    anchor + "\n\\usepackage{float}",
                    1,
                )
                break
        else:
            text = text.replace(
                r"\usepackage{cancel}",
                "\\usepackage{cancel}\n\\usepackage{float}",
                1,
            )
    text = re.sub(r"\\begin\{figure\}\[[^\]]*\]", r"\\begin{figure}[H]", text)
    text = re.sub(r"\\begin\{figure\}(?!\[)", r"\\begin{figure}[H]", text)
    return text


def _unnumbered_cover_section(text):
    """First numbered \\section after \\begin{document} is the Notion page title."""
    doc = text.find(r"\begin{document}")
    if doc == -1:
        return text
    m = re.search(r"(?<!\\section\*)\\section\{", text[doc:])
    if not m:
        return text
    start = doc + m.start()
    return text[:start] + r"\section*{" + text[start + len(r"\section{") :]


def _enable_hyperref_links(text):
    """Visible PDF links (TOC, cross-refs, URLs)."""
    if "colorlinks=true" in text:
        return text
    return text.replace(
        "hidelinks",
        "colorlinks=true,\n  linkcolor=blue!70!black,\n  urlcolor=blue",
        1,
    )


def _add_roman_frontmatter_pagenumbering(text: str) -> str:
    """Cover + index use roman numerals (i, ii, …)."""
    if re.search(
        r"\\begin\{document\}\s*\n\s*\\pagenumbering\{roman\}\s*\n\s*\\setcounter\{page\}\{1\}",
        text,
    ):
        return text
    doc_roman = "\\begin{document}\n\\pagenumbering{roman}\n\\setcounter{page}{1}"
    text = re.sub(
        r"\\begin\{document\}(?:\\n\\+)?\\pagenumbering\{roman\}(?:\\n\\+)?\\setcounter\{page\}\{1\}",
        lambda _: doc_roman,
        text,
        count=1,
    )
    if r"\pagenumbering{roman}" not in text:
        text = text.replace(
            r"\begin{document}",
            "\\begin{document}\n\\pagenumbering{roman}\n\\setcounter{page}{1}",
            1,
        )
    return text


def _ensure_arabic_mainmatter_pagenumbering(text: str) -> str:
    """Body chapters start at page 1 (arabic); TOC entries match real page numbers."""
    if r"\pagenumbering{arabic}" in text:
        return text
    m = re.search(r"\\tableofcontents\s*(?:\n|\\clearpage)", text)
    if not m:
        return text
    insert_at = m.end()
    # Skip blank lines / newpage already following the TOC
    while insert_at < len(text) and text[insert_at] in "\n\r":
        insert_at += 1
    if text[insert_at : insert_at + len(r"\newpage")] == r"\newpage":
        insert_at += len(r"\newpage")
        while insert_at < len(text) and text[insert_at] in "\n\r":
            insert_at += 1
    arabic_block = "\\pagenumbering{arabic}\n\\setcounter{page}{1}\n\n"
    return text[:insert_at] + arabic_block + text[insert_at:]


def _add_table_of_contents(text):
    """
    Clickable TOC after the cover page (hyperref/bookmark).
    Front matter uses roman page numbers; main text uses arabic from page 1.
    Requires two pdflatex runs to refresh page numbers.
    """
    text = _add_roman_frontmatter_pagenumbering(text)

    if r"\tableofcontents" in text:
        text = _ensure_arabic_mainmatter_pagenumbering(text)
        return text, 0

    if r"\setcounter{tocdepth}" not in text:
        text = text.replace(
            r"\setcounter{secnumdepth}{3}",
            r"\setcounter{secnumdepth}{3}"
            + "\n"
            + r"\setcounter{tocdepth}{3} % TOC: section, subsection, subsubsection",
            1,
        )

    toc_block = (
        "\n\\newpage\n"
        "\\section*{Indice}\n"
        "\\tableofcontents\n"
        "\\newpage\n"
        "\\pagenumbering{arabic}\n"
        "\\setcounter{page}{1}\n\n"
    )

    pos = _toc_insertion_point(text)
    if pos is None:
        return text, 0

    return text[:pos] + toc_block + text[pos:], 1


def _toc_insertion_point(text: str) -> int | None:
    """
    Place the TOC after the cover (title + properties), before the first body chapter.

    The Notion page title is \\section*; the first numbered \\section is body content.
    """
    numbered = list(re.finditer(r"(?<!\\section\*)\\section\{", text))
    if numbered:
        return numbered[0].start()
    return None


def _unicode_preamble():
    return "\n" + "\n".join(unicode_preamble_lines()) + "\n\\begin{document}\n"


def _fix_pandoc_char_escapes(text):
    """Replace Pandoc \\char\"XXXX with a LaTeX command when mapped."""

    def repl(match: re.Match[str]) -> str:
        hex_code = match.group(1)
        latex = latex_for_codepoint(hex_code)
        if latex is None:
            return match.group(0)
        need_space = (
            match.end() < len(text)
            and text[match.end()].isalpha()
            and re.fullmatch(r"\\[a-zA-Z]+", latex) is not None
        )
        latex_out = latex + (" " if need_space else "")
        if hex_code in UNICODE_TEXT:
            return latex_out
        return rf"\ensuremath{{{latex_out}}}"

    text = re.sub(
        r'\\char\s*"\s*([0-9A-Fa-f]{3,4})',
        repl,
        text,
    )
    return separate_glued_command_letters(text)


def _strip_trailing_backslash(formula):
    """Remove trailing \\\\ that break gather* environments."""
    formula = formula.rstrip()
    while formula.endswith("\\\\"):
        formula = formula[:-2].rstrip()
    return formula


def _unwrap_gather_with_environments(text):
    """gather* wrapping cases/array breaks compilation."""

    def replace(match):
        content = match.group(1)
        if re.search(r"\\begin\{", content):
            return f"\\[{content}\\]"
        return match.group(0)

    return re.sub(
        r"\\begin\{gather\*\}(.*?)\\end\{gather\*\}",
        replace,
        text,
        flags=re.DOTALL,
    )


def _fix_cases_environments(text):
    """Fix alignment and blank lines in cases environments."""

    def clean(match):
        body = match.group(1)
        body = re.sub(r"&&&", r"&", body)
        body = re.sub(r"&&", r"&", body)
        body = re.sub(r"\n\s*\n", "\n", body)
        return "\\begin{cases}" + body + "\\end{cases}"

    return re.sub(
        r"\\begin\{cases\}(.*?)\\end\{cases\}",
        clean,
        text,
        flags=re.DOTALL,
    )


def _deescape_pandoc_latex(text):
    """Restore LaTeX commands escaped by Pandoc."""
    text = re.sub(r"\\textbackslash text\s*\{", r"\\text{", text)
    text = re.sub(r"\\textbackslash texttt\s*\{", r"\\texttt{", text)
    for color in ("red", "green", "blue", "yellow", "purple", "gray"):
        text = re.sub(
            rf"\\textbackslash {color}\{{",
            rf"\\textcolor{{{color}}}{{",
            text,
        )
    # Longer commands first (avoid turning \\textbackslash includegraphics into \\in)
    for cmd in ("includegraphics", "subseteq", "Rightarrow", "exists", "forall", "mathbb"):
        text = re.sub(rf"\\textbackslash {cmd}\b", rf"\\{cmd}", text)
    commands = (
        "geq",
        "leq",
        "cup",
        "cap",
        "empty",
        "wedge",
        "aleph",
        "Sigma",
        "Gamma",
        "Delta",
    )
    for cmd in commands:
        text = re.sub(rf"\\textbackslash {cmd}\b", rf"\\{cmd}", text)
    text = re.sub(r"\\textbackslash \{", r"\\{", text)
    text = re.sub(r"\\textbackslash \}", r"\\}", text)
    return text


def _fix_literal_backslash_n_in_preamble(text: str) -> str:
    """Repair literal ``\\n`` typos in the preamble and after \\begin{document}."""
    text = re.sub(
        r"(\\usepackage\{[^}]+\})\\n(\\usepackage)",
        r"\1\n\2",
        text,
    )
    text = text.replace(
        r"\begin{document}\n\\pagenumbering",
        "\\begin{document}\n\\pagenumbering",
    )
    roman_counter = "\\pagenumbering{roman}\n\\setcounter{page}{1}"
    text = re.sub(
        r"\\pagenumbering\{roman\}\\n\\+setcounter\{page\}\{1\}",
        lambda _: roman_counter,
        text,
    )
    return text


_PANDOC_STRIKEOUT_BLOCK = re.compile(
    r"\\ifLuaTeX\s*\n"
    r"\s*\\usepackage\{luacolor\}\s*\n"
    r"\s*\\usepackage\[soul\]\{lua-ul\}\s*\n"
    r"\\else\s*\n"
    r"\s*\\usepackage\{soul\}\s*\n"
    r"\\fi",
    re.MULTILINE,
)


def _ensure_strikeout_support(text: str) -> str:
    """
    Pandoc loads ``soul`` for underline/strikeout; TeX Live basic often lacks it.

    Fall back to ``ulem`` (or no-op macros) so pdflatex does not stop on missing soul.sty.
    """
    strikeout_block = (
        "\\ifLuaTeX\n"
        "  \\usepackage{luacolor}\n"
        "  \\IfFileExists{lua-ul.sty}{\\usepackage[soul]{lua-ul}}{}\n"
        "\\else\n"
        "  \\IfFileExists{soul.sty}{\\usepackage{soul}}{"
        "\\IfFileExists{ulem.sty}{\\usepackage[normalem]{ulem}}{"
        "\\providecommand{\\sout}[1]{#1}\\providecommand{\\ul}[1]{#1}}"
        "}}\n"
        "\\fi"
    )
    return _PANDOC_STRIKEOUT_BLOCK.sub(lambda _: strikeout_block, text, count=1)


def _ensure_grffile(text: str) -> str:
    """Allow spaces and commas in image paths."""
    if r"\usepackage{grffile}" in text:
        return text
    if r"\usepackage{graphicx}" in text:
        return text.replace(
            r"\usepackage{graphicx}",
            "\\usepackage{graphicx}\n\\usepackage{grffile}",
            1,
        )
    return text


def _fix_figure_images(text: str, tex_path: str | Path = ".") -> str:
    """Repair Pandoc image markup so pdfLaTeX embeds PNGs instead of broken links."""
    text = neutralize_pandocbounded_scale(text)
    text = re.sub(
        r"\\in\s*cludegraphics",
        r"\\includegraphics",
        text,
        flags=re.IGNORECASE,
    )

    graphics_re = (
        r"(\\includegraphics(?:\[[^\]]*\])?\{[^{}]+\})"
    )

    def _unwrap_pandocbounded(m: re.Match[str]) -> str:
        return m.group(1)

    text = re.sub(
        rf"\\href\{{[^{{}}]+\}}\{{\\pandocbounded\{{{graphics_re}\}}\}}",
        _unwrap_pandocbounded,
        text,
    )
    text = re.sub(
        rf"\\pandocbounded\{{{graphics_re}\}}",
        _unwrap_pandocbounded,
        text,
    )
    text = unwrap_href_includegraphics(text)

    def _quote_image_path(m: re.Match[str]) -> str:
        opts = m.group(1) or ""
        path = m.group(2).strip()
        if path.startswith('"') and path.endswith('"'):
            return m.group(0)
        if " " in path or "," in path:
            escaped = path.replace('"', "'")
            return f'\\includegraphics{opts}{{"{escaped}"}}'
        return m.group(0)

    text = re.sub(
        r"\\includegraphics(\[[^\]]*\])?\{([^{}]+)\}",
        _quote_image_path,
        text,
    )

    work_dir = Path(tex_path).parent
    text, _ = fix_includegraphics_paths(text, work_dir)

    clean_html = work_dir / f"{Path(tex_path).stem}_clean.html"
    widths = load_image_width_map(clean_html)
    text = apply_widths_to_includegraphics(text, widths)
    text = center_figure_images(text)
    return text


def _pandoc_dollars_to_latex(content):
    """Convert \\$ ... \\$ (Pandoc) body to LaTeX math."""
    s = content.strip()
    s = re.sub(r"\\textbar\s*([^\\]+?)\\textbar\{\}?", r"|\1|", s)
    s = s.replace(r"\textbar", "|")
    s = s.replace(r"\textless", "<").replace(r"\textgreater", ">")
    s = re.sub(r"<\s+", "<", s)
    s = re.sub(r"\s+>", ">", s)
    s = re.sub(r"\\textbackslash\s*,", ",", s)
    s = re.sub(r"\\textquotesingle", "'", s)
    s = _deescape_pandoc_latex(s)
    s = re.sub(r"\\textbackslash\s+([A-Za-z]+)", r"\\\1", s)
    # Literal "^" and "{"/"}" typed as prose (not a real Notion equation) are
    # escaped by Pandoc as the text-mode accent \^{} and literal \{ \}; once
    # this span is math, un-escape them so ^ acts as the superscript operator.
    s = s.replace(r"\^{}", "^")
    s = re.sub(r"\\([{}])", r"\1", s)
    s = normalize_katex_in_document(s)
    s = s.replace(r"\_", "_")
    s = re.sub(r"\^\{\}", "^", s)
    s = re.sub(r"\^\{([^}]+)\}", r"^{\1}", s)
    s = re.sub(r"\{\}", "", s)
    return s.strip()


def _looks_like_math(text):
    if not text or len(text) > 200:
        return False
    if "\n\n" in text:
        return False
    if re.search(r"\\begin\{|\\end\{|\\section|\\item", text):
        return False
    if re.search(
        r"\\textbackslash|\\textbar|\\_|\\text[<{]|\\Sigma|\\aleph|\^{",
        text,
    ):
        return True
    return bool(re.fullmatch(r"[\s0-9A-Za-z|+*/=<>(){}[\].,_\\^-]+", text))


def _fix_escaped_dollar_math(text):
    """
    Convert \\$ ... \\$ (or \\$\\$ ... \\$\\$, from literal $$ pseudo-math in prose)
    to \\( ... \\) for inline math.
    """
    count = 0
    pattern = re.compile(
        r"\\\$\\?\$?\s*"
        r"((?:[^\n$\\]|\\(?!begin\{|\\end\{|\\section))+?)"
        r"\s*\\\$\\?\$?",
        re.DOTALL,
    )

    def repl(match):
        nonlocal count
        inner = match.group(1)
        if not _looks_like_math(inner):
            return match.group(0)
        latex = _pandoc_dollars_to_latex(inner)
        count += 1
        return f"\\({latex}\\)"

    text = pattern.sub(repl, text)
    return text, count


def _plain_bookmark(text):
    """ASCII-safe version for PDF bookmarks."""
    s = text.replace("\n", " ")
    s = re.sub(r"\\[()$]", "", s)
    s = re.sub(r"\\text\s+", "", s)
    s = re.sub(r"\\text\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\texttt\{([^}]*)\}", r"\1", s)
    s = re.sub(r"_\{([^}]*)\}", r"_\1", s)
    s = s.replace(r"\_", "_")
    s = re.sub(r"[_^{}\\]", "", s)
    s = s.replace("#", "").replace("%", "")
    return re.sub(r"\s+", " ", s).strip()


def _read_braced_argument(text, start):
    """Read a braced argument starting at '{'."""
    if start >= len(text) or text[start] != "{":
        return None, start
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
        i += 1
    return None, start


def _fix_texorpdfstring_bookmarks(text):
    """Clean the second argument of \\texorpdfstring (PDF bookmark)."""
    marker = r"\texorpdfstring"
    out = []
    pos = 0
    count = 0

    while True:
        start = text.find(marker, pos)
        if start == -1:
            out.append(text[pos:])
            break
        out.append(text[pos:start])
        i = start + len(marker)
        if i >= len(text) or text[i] != "{":
            out.append(text[start:])
            break
        visible, i = _read_braced_argument(text, i)
        if visible is None:
            out.append(text[start:])
            break
        if i >= len(text) or text[i] != "{":
            out.append(text[start:])
            break
        bookmark, i = _read_braced_argument(text, i)
        if bookmark is None:
            out.append(text[start:])
            break
        if "textbackslash" in bookmark:
            visible = visible.replace("\n", " ").strip()
            new_bm = _plain_bookmark(visible)
            out.append(f"\\texorpdfstring{{{visible}}}{{{new_bm}}}")
            count += 1
        else:
            out.append(text[start:i])
        pos = i

    return "".join(out), count


def _fix_section_titles(text):
    """
    Fix \\section/\\subsection titles corrupted by Pandoc
    (\\$...\\$, textbackslash, duplicates like ATM...ATM).
    """
    commands = r"section|subsection|subsubsection|paragraph|subparagraph"
    pattern = re.compile(
        rf"(\\(?:{commands})\*?)\{{(.*?)\}}",
        re.DOTALL,
    )
    fixed = 0

    def fix(match):
        nonlocal fixed
        command, title = match.group(1), match.group(2)
        if "textbackslash" not in title and r"\$" not in title:
            return match.group(0)

        title = title.replace(r"\hspace{0pt}", "")
        for z in ("\ufeff", "\u200b"):
            title = title.replace(z, "")

        title = _deescape_pandoc_latex(title)
        title = " ".join(title.split())

        title = re.sub(
            r"([A-Z]{2,})\\text\{([^}]+)\}_\\text\{([^}]+)\}\1",
            r"\\text{\2}_{\\text{\3}}",
            title,
        )
        title = re.sub(
            r"([A-Z]{2,})\\text\s+([A-Za-z])_\{\\text\{([^}]+)\}\}\1",
            r"\\text{\2}_{\\text{\3}}",
            title,
        )

        math_match = re.search(r"\\\$(.*?)\\\$", title)
        if math_match:
            math_expr = math_match.group(1).replace(r"\_", "_")
            prefix = title[: math_match.start()].strip()
            suffix = title[math_match.end() :].strip()
            plain = _plain_bookmark(f"{prefix} {math_expr} {suffix}")
            if prefix:
                title = (
                    f"{prefix} \\texorpdfstring{{\\({math_expr}\\)}}{{{plain}}}"
                )
            else:
                title = f"\\texorpdfstring{{\\({math_expr}\\)}}{{{plain}}}"
        elif re.search(r"\\text\{|\\texttt\{", title):
            plain = _plain_bookmark(title)
            title = f"\\texorpdfstring{{\\({title}\\)}}{{{plain}}}"

        fixed += 1
        return f"{command}{{{title}}}"

    text = pattern.sub(fix, text)
    return text, fixed


def _fix_escaped_inline_math(text):
    """Fix inline body math: \\$ \\textbackslash text ... \\$."""
    text = re.sub(
        r"\\\$\s*\\textbackslash text\s+([A-Za-z])\\?_\{"
        r"\\textbackslash text\{([^}]+)\}\}\s*\\\$",
        r"\\(\\text{\1}_{\\text{\2}}\\)",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"\\\$\s*\\textbackslash text\{([^}]+)\}"
        r"_\\textbackslash text\{([^}]+)\}\s*\\\$",
        r"\\(\\text{\1}_{\\text{\2}}\\)",
        text,
        flags=re.DOTALL,
    )
    return text


def _remove_empty_captions(text):
    """Remove empty \\caption/\\label under figures (no 'Figure N' noise)."""
    marker = r"\caption{"
    out = []
    pos = 0
    count = 0

    while True:
        start = text.find(marker, pos)
        if start == -1:
            out.append(text[pos:])
            break
        out.append(text[pos:start])
        i = start + len(marker) - 1
        _, i = _read_braced_argument(text, i)
        if i >= len(text):
            out.append(text[start:])
            break
        rest = text[i : i + 30]
        if rest.lstrip().startswith(r"\label{"):
            j = text.find(r"\label{", i)
            _, i = _read_braced_argument(text, j)
            count += 1
        pos = i

    text = "".join(out)
    text, n_label = re.subn(
        r"\s*\\label\{[^}]+\}\s*(?=\\end\{figure\})",
        "\n",
        text,
    )
    text, n_lt = re.subn(
        r"\\caption\{[^}]*\}\\label\{[^}]+\}\s*\\tabularnewline",
        r"\\tabularnewline",
        text,
    )
    return text, count + n_label + n_lt


def _fix_display_math_blocks(text):
    """Convert multiline \\[...\\] to gather* only when safe."""

    pattern = re.compile(r"\\\[(.*?)\\\]", re.DOTALL)
    n_gather = 0

    def fix(match):
        nonlocal n_gather
        formula = _strip_trailing_backslash(match.group(1))
        if re.search(r"\\begin\{", formula):
            return f"\\[{formula}\\]"
        if "\\\\" in formula:
            n_gather += 1
            return f"\\begin{{gather*}}{formula}\\end{{gather*}}"
        return f"\\[{formula}\\]"

    text = pattern.sub(fix, text)
    return text, n_gather


def fix_latex(tex_path):
    from notion2tex.console import console

    try:
        with open(tex_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        console.error(f"LaTeX not found: {tex_path}")
        return

    text = _fix_literal_backslash_n_in_preamble(text)
    text = _ensure_strikeout_support(text)
    text = _enable_section_numbering(text)
    text = _unnumbered_cover_section(text)
    text = _enable_hyperref_links(text)
    text, n_toc = _add_table_of_contents(text)
    text = _fix_figure_placement(text)
    text = _ensure_grffile(text)

    if not has_unicode_preamble(text):
        text = text.replace(r"\begin{document}", _unicode_preamble())

    text = normalize_katex_in_document(text)
    text = _fix_figure_images(text, tex_path)
    text = text.replace("├", r"\vdash")
    text = _fix_pandoc_char_escapes(text)

    text = _fix_cases_environments(text)
    text = _unwrap_gather_with_environments(text)
    text, n_gather = _fix_display_math_blocks(text)
    text, n_titles = _fix_section_titles(text)
    text, n_bookmark = _fix_texorpdfstring_bookmarks(text)
    text = _fix_escaped_inline_math(text)
    text, n_dollar = _fix_escaped_dollar_math(text)
    text, n_caption = _remove_empty_captions(text)
    text, n_tables = improve_tables_in_document(text)
    text, n_toggle_items = _unwrap_paragraph_itemize(text)

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(text)

    parts = [
        f"gather* {n_gather}",
        f"titles {n_titles}",
        f"bookmarks {n_bookmark}",
        f"inline math {n_dollar}",
        f"captions {n_caption}",
        f"tables {n_tables}",
    ]
    if n_toc:
        parts.append("TOC added")
    if n_toggle_items:
        parts.append(f"toggle lists {n_toggle_items}")
    console.detail("Fixes applied → " + ", ".join(parts))


if __name__ == "__main__":
    default_tex = "output.tex"
    if len(sys.argv) > 1:
        default_tex = sys.argv[1]

    fix_latex(default_tex)

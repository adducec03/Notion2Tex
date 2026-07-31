import re
import sys
from pathlib import Path

from notion2tex.table_latex import improve_tables_in_document
from notion2tex.image_paths import fix_includegraphics_paths
from notion2tex.image_sizes import (
    align_figure_images,
    apply_widths_to_includegraphics,
    load_image_alignment_map,
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


def _build_cover_page(text: str) -> str:
    """
    Pandoc's \\maketitle (from the HTML <title>) and the Notion page's own
    <h1 class="page-title"> both carry the same title text, so the plain
    pipeline renders it twice: once via \\maketitle, again as a redundant
    \\section*{title} right after the cover image. Replace both with a
    single designed title page: a large centered title above the cover
    image (capped so a tall photo can't run off the page), vertically
    balanced, no header/footer.

    Falls back to leaving the text untouched if there's no cover image
    right after \\maketitle (page has no cover photo) — the plain
    \\maketitle + \\section* title still work, just without this polish.
    """
    maketitle = text.find(r"\maketitle")
    if maketitle == -1:
        return text

    window = text[maketitle : maketitle + 400]
    image_match = re.search(r"\\includegraphics\[[^\]]*\]\{[^{}]+\}", window)
    if not image_match:
        return text
    image = image_match.group(0)
    image_end = maketitle + image_match.end()

    section_match = re.match(r"\s*\\section\*\{", text[image_end : image_end + 200])
    if not section_match:
        return text
    brace_start = image_end + section_match.end() - 1
    title, after_title = _read_braced_argument(text, brace_start)
    if title is None:
        return text

    label_match = re.match(r"\\label\{[^{}]*\}\s*", text[after_title:])
    end = after_title + (label_match.end() if label_match else 0)
    label = label_match.group(0) if label_match else ""

    sized_image = re.sub(
        r"width=\\linewidth",
        r"width=\\linewidth,height=0.55\\textheight",
        image,
        count=1,
    )
    cover = (
        "\\thispagestyle{empty}\n"
        "\\begin{center}\n"
        "\\vspace*{\\fill}\n"
        f"{{\\Huge\\bfseries {title}}}{label}\n"
        "\\vspace{2em}\n\n"
        f"{sized_image}\n\n"
        "\\vfill\n"
        "\\end{center}\n"
        "\\clearpage\n"
    )
    return text[:maketitle] + cover + text[end:]


def _enable_hyperref_links(text):
    """Visible PDF links (TOC, cross-refs, URLs)."""
    if "colorlinks=true" in text:
        return text
    return text.replace(
        "hidelinks",
        "colorlinks=true,\n  linkcolor=blue!70!black,\n  urlcolor=blue",
        1,
    )


_DARK_PAGE_BACKGROUND = "30,30,30"
_DARK_BODY_TEXT = "225,225,225"
_DARK_LINK = "88,166,255"


def _apply_dark_theme(text: str) -> str:
    """
    --dark: a dark gray (not pure black) page with light text.

    Call this LAST, after every other fix has run (tables, callouts, the
    fancyhdr header/footer, ...): headers/footers and float environments
    (\\begin{table}, \\begin{figure}) are composed by LaTeX in a separate box
    construction that does not inherit the \\color set for the main text
    flow — confirmed by inspecting the actual PDF content stream, where
    those regions use the plain DeviceGray "0" (black) operator instead of
    our RGB color, even though \\color{notiondarktext} is active everywhere
    else. Each of those needs its own explicit \\color{} instead of relying
    on the ambient one. Same story for fancyhdr's \\headrule (its own \\hrule
    box, drawn outside \\fancyhead's color scope) and for the TOC's page
    numbers, which the LaTeX kernel's \\@dottedtocline hardcodes back to
    \\normalcolor regardless of the ambient color.

    Runs after _enable_hyperref_links, so its blue-on-white link colors
    (picked for a light page) can be swapped for something that stays
    readable on a dark background. The Lua filter's highlight/callout/quote
    colors are switched separately (it reads the same NOTION2TEX_DARK env
    var the pipeline sets when --dark is passed to pandoc), and code blocks
    get pandoc's "breezedark" syntax theme instead of the default.
    """
    if r"\pagecolor" in text:
        return text

    text = text.replace(
        r"\usepackage{xcolor}",
        "\\usepackage{xcolor}\n"
        f"\\definecolor{{notiondarkbg}}{{RGB}}{{{_DARK_PAGE_BACKGROUND}}}\n"
        f"\\definecolor{{notiondarktext}}{{RGB}}{{{_DARK_BODY_TEXT}}}\n"
        f"\\definecolor{{notiondarklink}}{{RGB}}{{{_DARK_LINK}}}\n",
        1,
    )
    text = text.replace(
        "linkcolor=blue!70!black,\n  urlcolor=blue",
        "linkcolor=notiondarklink,\n  urlcolor=notiondarklink",
        1,
    )

    # fancyhdr composes the header/footer separately from the body text.
    text = text.replace(
        r"\fancyhead[C]{\rightmark}",
        "\\fancyhead[C]{\\color{notiondarktext}\\rightmark}",
        1,
    )
    text = text.replace(
        r"\fancyfoot[C]{\thepage}",
        "\\fancyfoot[C]{\\color{notiondarktext}\\thepage}",
        1,
    )
    # \headrule (the thin line under the header) is its own \hrule box, drawn
    # after \fancyhead's color scope has already closed — still black otherwise.
    text = text.replace(
        r"\renewcommand{\headrulewidth}{0.4pt}",
        "\\renewcommand{\\headrulewidth}{0.4pt}\n"
        "\\makeatletter\n"
        "\\renewcommand{\\headrule}{{\\color{notiondarktext}"
        "\\hrule\\@height\\headrulewidth\\@width\\headwidth\\vskip-\\headrulewidth}}\n"
        "\\makeatother",
        1,
    )

    # \begin{table}/\begin{figure} are floats; same box-isolation issue.
    text = re.sub(
        r"\\begin\{(table|figure)\}\[H\]",
        lambda m: m.group(0) + "\\color{notiondarktext}",
        text,
    )

    return text.replace(
        r"\begin{document}",
        "\\begin{document}\n"
        "\\pagecolor{notiondarkbg}\n"
        "\\color{notiondarktext}\n"
        # The LaTeX kernel's TOC line macro (\@dottedtocline) hardcodes
        # "\normalfont\normalcolor" around the page number, resetting past
        # our ambient \color — redefining \normalcolor itself is the fix.
        "\\renewcommand{\\normalcolor}{\\color{notiondarktext}}\n",
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

    # \tableofcontents (article class) already emits its own heading —
    # \section*{\contentsname} — before the entries. No need to write one
    # ourselves; doing so used to produce two stacked headings on the TOC
    # page ("Indice" then "Contents"), since neither knew about the other.
    toc_block = (
        "\n\\newpage\n"
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


def _start_chapters_on_new_page(text: str) -> str:
    """
    Each top-level chapter (\\section, the cover title excluded since it's
    already \\section*) starts on its own page instead of wherever it falls
    mid-page. The first chapter already gets one from the TOC block's own
    trailing \\newpage; \\clearpage there is a harmless no-op.
    """
    return re.sub(
        r"(?<!\\section\*)\\section\{",
        lambda m: "\\clearpage\n" + m.group(0),
        text,
    )


def _remove_maketitle(text: str) -> str:
    """
    Non-book mode: no separate title page. Pandoc's \\maketitle would
    otherwise duplicate the Notion page's own heading (the first
    \\section{...}, from its <h1 class="page-title">) right underneath it —
    drop \\maketitle and let that heading serve as the document's own
    title, like any other section.
    """
    return re.sub(r"\\maketitle\s*\n*", "", text, count=1)


def _add_running_chapter_header(text: str) -> str:
    """
    Book-style running header: the current chapter (\\section) name at the
    top of every page.

    Two article-class quirks need overriding, or the header is useless:
    1. By default \\subsection (not \\section) is what updates \\rightmark,
       so the header would show the last subsection title instead of
       staying on the chapter name throughout.
    2. A mark set by the sectioning command that opens a fresh page isn't
       picked up for that same page's header (a well-known TeX/marks
       quirk) — it only shows starting from the *next* page, so a
       chapter's own opening page would show the *previous* chapter's name.
    Explicitly redefining \\sectionmark (via \\markright) and blanking
    \\subsectionmark fixes both: verified empirically, not just from the
    kernel docs, since the exact mark semantics are notoriously fiddly.

    The cover title is \\section* (unnumbered), which never touches marks,
    so it and the TOC page (its own \\tableofcontents call marks itself as
    "Contents") naturally show no chapter name.
    """
    if r"\usepackage{fancyhdr}" in text:
        return text
    block = (
        "\\usepackage{fancyhdr}\n"
        "\\pagestyle{fancy}\n"
        "\\fancyhf{}\n"
        "\\fancyhead[C]{\\rightmark}\n"
        "\\fancyfoot[C]{\\thepage}\n"
        "\\renewcommand{\\headrulewidth}{0.4pt}\n"
        "\\renewcommand{\\sectionmark}[1]{\\markright{#1}}\n"
        "\\renewcommand{\\subsectionmark}[1]{}\n"
    )
    return text.replace(r"\begin{document}", block + r"\begin{document}", 1)


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


def _unwrap_align_inside_gathered(text):
    """
    \\[\\begin{gathered}\\begin{align*}...\\end{align*}\\end{gathered}\\]
    is invalid: align/align*/alignat/flalign are themselves top-level
    display-math starters and cannot nest inside gathered (which already
    expects to sit directly inside \\[...\\]). Left as-is, this desyncs
    math mode for pdfTeX and cascades into hundreds of unrelated
    "Undefined control sequence"/"Missing $ inserted" errors for the rest
    of the document. Seen coming straight from equations authored this way
    in Notion itself. When gathered's only content is one such block, drop
    the outer \\[...\\]/gathered wrapper and keep the align block alone.
    """
    pattern = re.compile(
        r"\\\[\s*\\begin\{gathered\}\s*"
        r"(\\begin\{(align\*?|alignat\*?|flalign\*?)\}.*?\\end\{\2\})"
        r"\s*\\end\{gathered\}\s*\\\]",
        re.DOTALL,
    )
    return pattern.sub(lambda m: m.group(1), text)


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


_BLANK_LINE_MATH_ENVS = (
    "gathered",
    "gather\\*?",
    "align\\*?",
    "alignat\\*?",
    "flalign\\*?",
    "aligned",
    "split",
)
_BLANK_LINE_MATH_ENV_RE = re.compile(
    r"\\begin\{(" + "|".join(_BLANK_LINE_MATH_ENVS) + r")\}(.*?)\\end\{\1\}",
    re.DOTALL,
)


def _strip_blank_lines_in_math_environments(text):
    """
    A blank line inside an amsmath multi-line environment becomes \\par at
    typeset time, which is illegal in math mode: pdfTeX reports
    "Missing $ inserted" and the failure cascades into dozens of unrelated-
    looking errors through the rest of the document. Notion equations are
    often typed with a blank line between rows for readability in the
    source editor — strip them here before pdflatex ever sees them.
    """

    def clean(match):
        env = match.group(1)
        body = re.sub(r"\n[ \t]*\n+", "\n", match.group(2))
        return f"\\begin{{{env}}}{body}\\end{{{env}}}"

    return _BLANK_LINE_MATH_ENV_RE.sub(clean, text)


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


_SOUL_MACRO_USE_RE = re.compile(r"\\(?:ul|sout|st|hl)\{")


def _ensure_strikeout_support(text: str) -> str:
    """
    Pandoc loads ``soul`` for underline/strikeout; TeX Live basic often lacks it.

    Fall back to ``ulem`` (or no-op macros) so pdflatex does not stop on missing soul.sty.

    Pandoc only emits its own soul-loading block when it recognizes a native
    Strikeout AST node. Underline (\\ul{}) and highlight (\\hl{}/\\sethlcolor)
    are injected as raw LaTeX by our own Lua filter and never trigger that —
    so a document using underline/highlight but no strikethrough gets no
    soul/ulem package at all from Pandoc, and pdflatex chokes on \\ul{}
    ("Undefined control sequence"). Insert the same fallback block
    ourselves whenever the body actually uses one of these macros.

    The true/false branches use boolean flags (\\ifNTX...\\fi), not raw
    \\providecommand text nested directly inside \\IfFileExists{}{}{}'s own
    braced arguments — the latter needs its "#1" doubled to "##1" per level
    of \\IfFileExists nesting (each one performs its own internal \\def
    capture of its branches), which is exactly the kind of thing that's easy
    to get wrong; verified by direct pdflatex compilation that the flag-based
    version below does not hit "Illegal parameter number" on a system where
    soul.sty is missing. ulem also has no \\ul (only \\uline) or highlight
    support at all, so those need explicit handling in the ulem branch too.
    """
    strikeout_block = (
        "\\ifLuaTeX\n"
        "  \\usepackage{luacolor}\n"
        "  \\IfFileExists{lua-ul.sty}{\\usepackage[soul]{lua-ul}}{}\n"
        "\\else\n"
        "  \\newif\\ifNTXSoulFound\n"
        "  \\newif\\ifNTXUlemFound\n"
        "  \\IfFileExists{soul.sty}{\\NTXSoulFoundtrue}{\\NTXSoulFoundfalse}\n"
        "  \\ifNTXSoulFound\n"
        "    \\usepackage{soul}\n"
        "  \\else\n"
        "    \\IfFileExists{ulem.sty}{\\NTXUlemFoundtrue}{\\NTXUlemFoundfalse}\n"
        "    \\ifNTXUlemFound\n"
        "      \\usepackage[normalem]{ulem}\n"
        "      \\let\\ul\\uline\n"
        "      \\providecommand{\\hl}[1]{#1}\n"
        "      \\providecommand{\\sethlcolor}[1]{}\n"
        "    \\else\n"
        "      \\providecommand{\\sout}[1]{#1}\n"
        "      \\providecommand{\\ul}[1]{#1}\n"
        "      \\providecommand{\\hl}[1]{#1}\n"
        "      \\providecommand{\\sethlcolor}[1]{}\n"
        "    \\fi\n"
        "  \\fi\n"
        "\\fi"
    )
    if _PANDOC_STRIKEOUT_BLOCK.search(text):
        return _PANDOC_STRIKEOUT_BLOCK.sub(lambda _: strikeout_block, text, count=1)

    if r"\usepackage{soul}" in text or r"\usepackage[normalem]{ulem}" in text:
        return text
    if not _SOUL_MACRO_USE_RE.search(text):
        return text
    return text.replace(
        r"\begin{document}", strikeout_block + "\n\\begin{document}", 1
    )


_BABEL_LANGUAGES = {
    "en": "english",
    "it": "italian",
}


def _ensure_language_support(text: str, lang: str | None) -> str:
    """
    Load babel for *lang* (a short code like "en"/"it"), which translates
    kernel-generated strings (\\contentsname, used by \\tableofcontents'
    own heading and running-header mark) and switches hyphenation rules to
    match. No *lang* -> no babel, text unchanged: LaTeX's plain-English
    defaults (e.g. "Contents") apply, same as today without this flag.
    """
    if lang is None:
        return text
    babel_name = _BABEL_LANGUAGES[lang]
    if r"\usepackage[" + babel_name + "]{babel}" in text:
        return text
    return text.replace(
        r"\begin{document}",
        f"\\usepackage[{babel_name}]{{babel}}\n" + r"\begin{document}",
        1,
    )


_FONT_PACKAGES = {
    "serif": "\\usepackage{mathptmx}\n",
    "sans": "\\usepackage[scaled]{helvet}\n\\renewcommand{\\familydefault}{\\sfdefault}\n",
}


def _apply_font(text: str, font: str | None) -> str:
    """
    Layer a font package on top of Pandoc's default \\usepackage{lmodern}.
    Loading mathptmx/helvet *after* lmodern is the standard, safe way to
    override just the roman/sans family (lmodern's own math/mono stay) --
    no *font* leaves lmodern as the only font, today's look.
    """
    if font is None:
        return text
    block = _FONT_PACKAGES[font]
    if block in text:
        return text
    if r"\usepackage{lmodern}" in text:
        return text.replace(r"\usepackage{lmodern}", r"\usepackage{lmodern}" + "\n" + block, 1)
    return text.replace(r"\begin{document}", block + r"\begin{document}", 1)


def _apply_font_size(text: str, font_size: str | None) -> str:
    """
    Insert 10pt/11pt/12pt into \\documentclass[...]{article}'s (currently
    empty) options. No *font_size* leaves LaTeX's own 10pt default in
    place -- identical output to explicitly passing "10".
    """
    if font_size is None:
        return text

    def repl(match: re.Match[str]) -> str:
        existing = match.group(1).strip()
        opts = f"{existing},{font_size}pt" if existing else f"{font_size}pt"
        return f"\\documentclass[{opts}]"

    return re.sub(r"\\documentclass\[([^\]]*)\]", repl, text, count=1)


_PAPER_OPTIONS = {"a4": "a4paper", "letter": "letterpaper"}
_MARGIN_VALUES = {"narrow": "0.75in", "normal": "1in", "wide": "1.5in"}


def _ensure_page_geometry(text: str, paper: str | None, margins: str | None) -> str:
    """
    Always set an explicit page size/margins via the geometry package --
    unlike the other appearance options, this one isn't "off unless
    requested". Without it, the page size silently follows whatever the
    local TeX install's ambient default paper is (A4 on most European
    installs, Letter on most US ones): two people running the identical
    command could get differently-sized PDFs. Defaults: A4, 1in margins.
    """
    if r"{geometry}" in text:
        return text
    paper_opt = _PAPER_OPTIONS[paper or "a4"]
    margin_value = _MARGIN_VALUES[margins or "normal"]
    line = f"\\usepackage[{paper_opt},margin={margin_value}]{{geometry}}\n"
    return text.replace(r"\begin{document}", line + r"\begin{document}", 1)


def _apply_accent_color(text: str, accent_color: str | None) -> str:
    """
    Override the link color (light-mode blue, or --dark's own link color)
    with a user-chosen accent. Must run after both _enable_hyperref_links
    and _apply_dark_theme so it wins over whichever of those set the
    ambient link color last. No *accent_color* leaves those untouched.
    """
    if accent_color is None:
        return text
    if "notionaccent" in text:
        return text
    text = text.replace(
        r"\usepackage{xcolor}",
        "\\usepackage{xcolor}\n" f"\\definecolor{{notionaccent}}{{HTML}}{{{accent_color}}}\n",
        1,
    )
    text = text.replace(
        "linkcolor=blue!70!black,\n  urlcolor=blue",
        "linkcolor=notionaccent,\n  urlcolor=notionaccent",
        1,
    )
    text = text.replace(
        "linkcolor=notiondarklink,\n  urlcolor=notiondarklink",
        "linkcolor=notionaccent,\n  urlcolor=notionaccent",
        1,
    )
    return text


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


def _ensure_callout_and_quote_support(text: str) -> str:
    """
    tcolorbox (callouts, via the Lua filter's colored box) and framed's
    \\leftbar (quotes, via the Lua filter) aren't loaded by Pandoc's default
    template.
    """
    if r"\usepackage{tcolorbox}" not in text:
        text = text.replace(r"\begin{document}", "\\usepackage{tcolorbox}\n\\begin{document}", 1)
    if r"\usepackage{framed}" not in text:
        text = text.replace(r"\begin{document}", "\\usepackage{framed}\n\\begin{document}", 1)
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
    alignments = load_image_alignment_map(clean_html)
    text = align_figure_images(text, alignments)
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


def fix_latex(
    tex_path,
    dark: bool = False,
    book: bool = False,
    lang: str | None = None,
    font: str | None = None,
    font_size: str | None = None,
    paper: str | None = None,
    margins: str | None = None,
    accent_color: str | None = None,
):
    from notion2tex.console import console

    try:
        with open(tex_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        console.error(f"LaTeX not found: {tex_path}")
        return

    text = _fix_literal_backslash_n_in_preamble(text)
    text = _ensure_strikeout_support(text)
    text = _ensure_language_support(text, lang)
    text = _apply_font(text, font)
    text = _apply_font_size(text, font_size)
    text = _ensure_page_geometry(text, paper, margins)
    text = _enable_section_numbering(text)
    if book:
        text = _unnumbered_cover_section(text)
    text = _enable_hyperref_links(text)
    if book:
        text, n_toc = _add_table_of_contents(text)
        text = _start_chapters_on_new_page(text)
        text = _add_running_chapter_header(text)
    else:
        n_toc = 0
    text = _fix_figure_placement(text)
    text = _ensure_grffile(text)
    text = _ensure_callout_and_quote_support(text)

    if not has_unicode_preamble(text):
        text = text.replace(r"\begin{document}", _unicode_preamble())

    text = normalize_katex_in_document(text)
    text = _fix_figure_images(text, tex_path)
    if book:
        text = _build_cover_page(text)
    else:
        text = _remove_maketitle(text)
    text = text.replace("├", r"\vdash")
    text = _fix_pandoc_char_escapes(text)

    text = _fix_cases_environments(text)
    text = _strip_blank_lines_in_math_environments(text)
    text = _unwrap_align_inside_gathered(text)
    text = _unwrap_gather_with_environments(text)
    text, n_gather = _fix_display_math_blocks(text)
    text, n_titles = _fix_section_titles(text)
    text, n_bookmark = _fix_texorpdfstring_bookmarks(text)
    text = _fix_escaped_inline_math(text)
    text, n_dollar = _fix_escaped_dollar_math(text)
    text, n_caption = _remove_empty_captions(text)
    text, n_tables = improve_tables_in_document(text)
    text, n_toggle_items = _unwrap_paragraph_itemize(text)

    if dark:
        text = _apply_dark_theme(text)
    text = _apply_accent_color(text, accent_color)

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

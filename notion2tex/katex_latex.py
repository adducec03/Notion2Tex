"""
Normalize KaTeX / Notion math annotations to standard pdfLaTeX.

Applied to annotation strings in clean_html and to the full .tex in fix_latex.
"""

from __future__ import annotations

import re

from notion2tex.unicode_map import (
    UNICODE_MATH,
    latex_for_codepoint,
    separate_glued_command_letters,
)

# KaTeX color shorthands (\\red, \\green, …)
KATEX_COLORS = (
    "red",
    "green",
    "blue",
    "yellow",
    "purple",
    "gray",
    "grey",
    "brown",
    "orange",
    "pink",
    "black",
    "white",
    "cyan",
    "magenta",
)

# Single-char Unicode often left in KaTeX annotations → LaTeX command
_UNICODE_IN_MATH: dict[str, str] = {}
for _code, _cmd in UNICODE_MATH.items():
    try:
        _ch = chr(int(_code, 16))
        if len(_ch) == 1:
            _UNICODE_IN_MATH[_ch] = _cmd
    except ValueError:
        pass

# Curly / typographic quotes → ASCII for LaTeX math/text
_CURLY_QUOTES = (
    ("\u2018", "`"),
    ("\u2019", "'"),
    ("\u201c", "``"),
    ("\u201d", "''"),
    ("\u2013", "--"),
    ("\u2014", "---"),
    ("\u2026", r"\ldots"),
    ("\u00a0", " "),
)


def normalize_katex(latex: str) -> str:
    """Convert a KaTeX math string to pdfLaTeX-safe LaTeX."""
    if not latex or not latex.strip():
        return latex

    s = latex
    s = _replace_unicode_literals(s)
    s = _replace_curly_quotes(s)
    s = _strip_html_macros(s)
    s = _fix_href(s)
    s = _fix_macro_aliases(s)
    s = _fix_katex_colors(s)
    s = _fix_char_escapes(s)
    s = _fix_chi(s)
    s = _fix_text_and_texttt(s)
    s = _fix_frac_and_font_aliases(s)
    s = _fix_operator_spacing(s)
    s = separate_glued_command_letters(s)
    return s


def _fix_operator_spacing(s: str) -> str:
    """Insert space when an operator is followed by an uppercase letter or digit (e.g. \\geqK)."""
    ops = (
        r"\\geq",
        r"\\leq",
        r"\\neq",
        r"\\equiv",
        r"\\rightarrow",
        r"\\leftarrow",
        r"\\Rightarrow",
        r"\\Leftarrow",
        r"\\to",
        r"\\in",
        r"\\notin",
        r"\\subset",
        r"\\supset",
    )
    for op in ops:
        s = re.sub(rf"({op})([A-Z0-9])", r"\1 \2", s)
    s = re.sub(r"\\in\s*cludegraphics", r"\\includegraphics", s, flags=re.IGNORECASE)
    return s


def normalize_katex_in_document(text: str) -> str:
    """Normalize KaTeX constructs throughout a LaTeX document."""
    return normalize_katex(text)


def _replace_unicode_literals(s: str) -> str:
    for char, cmd in _UNICODE_IN_MATH.items():
        if char not in s:
            continue
        # μs, πf, … — do not let the command swallow the next letter
        s = re.sub(
            re.escape(char) + r"(?=[A-Za-z])",
            lambda _m, c=cmd: c + " ",
            s,
        )
        s = s.replace(char, cmd)
    return s


def _replace_curly_quotes(s: str) -> str:
    for old, new in _CURLY_QUOTES:
        s = s.replace(old, new)
    return s


def _strip_html_macros(s: str) -> str:
    """KaTeX HTML helpers (not supported in pdfLaTeX)."""
    for macro in ("htmlClass", "htmlId", "htmlStyle", "htmlData"):
        s = re.sub(
            rf"\\{macro}\s*\{{[^{{}}]*\}}\s*\{{([^{{}}]*)\}}",
            r"\1",
            s,
        )
    return s


def _fix_href(s: str) -> str:
    return re.sub(
        r"\\href\s*\{[^{}]*\}\s*\{([^{}]*)\}",
        r"\1",
        s,
    )


def _fix_macro_aliases(s: str) -> str:
    # Order matters: longer / compound forms first
    _W = r"(?![a-zA-Z])"
    replacements = [
        (rf"\\not\\exist{_W}", r"\\nexists"),
        (rf"\\not\\in{_W}", r"\\notin"),
        (rf"\\varnothing{_W}", r"\\emptyset"),
        (rf"\\empty{_W}", r"\\emptyset"),
        (rf"\\exist{_W}", r"\\exists"),
        (rf"\\bold{_W}", r"\\boldsymbol"),
        (rf"\\bm{_W}", r"\\boldsymbol"),
        (rf"\\Bbb{_W}", r"\\mathbb"),
        (rf"\\plusmn{_W}", r"\\pm"),
        (rf"\\minus{_W}", r"-"),
        (rf"\\dots{_W}", r"\\ldots"),
        (rf"\\iff{_W}", r"\\Leftrightarrow"),
        (rf"\\em{_W}", r"\\textit"),
        (rf"\\bf{_W}", r"\\mathbf"),
        (rf"\\it{_W}", r"\\mathit"),
        (rf"\\cal{_W}", r"\\mathcal"),
        (rf"\\scr{_W}", r"\\mathscr"),
        (rf"\\frak{_W}", r"\\mathfrak"),
        (rf"\\lvert{_W}", r"|"),
        (rf"\\rvert{_W}", r"|"),
        (rf"\\lVert{_W}", r"\\|"),
        (rf"\\rVert{_W}", r"\\|"),
        (rf"\\colon{_W}", r":"),
        (rf"\\lt{_W}", r"<"),
        (rf"\\gt{_W}", r">"),
        (rf"\\ne{_W}", r"\\neq"),
        (rf"\\le{_W}", r"\\leq"),
        (rf"\\ge{_W}", r"\\geq"),
        (rf"\\gets{_W}", r"\\leftarrow"),
        (rf"\\to{_W}", r"\\rightarrow"),
        (rf"\\doublerightarrow{_W}", r"\\Rightarrow"),
        (rf"\\doubleleftarrow{_W}", r"\\Leftarrow"),
        (rf"\\Colon{_W}", r"::"),
    ]
    for pattern, repl in replacements:
        s = re.sub(pattern, repl, s)
    return s


def _fix_katex_colors(s: str) -> str:
    for color in KATEX_COLORS:
        c = "gray" if color == "grey" else color
        s = re.sub(
            rf"\\{color}\s*\{{([^{{}}]*)\}}",
            rf"\\textcolor{{{c}}}{{\1}}",
            s,
        )
        s = re.sub(
            rf"\\{color}(?![a-zA-Z])",
            rf"\\color{{{c}}}",
            s,
        )
    return s


def _fix_char_escapes(s: str) -> str:
    def repl(match: re.Match[str]) -> str:
        hex_code = match.group(1)
        latex = latex_for_codepoint(hex_code)
        if latex is None:
            return match.group(0)
        return rf"\ensuremath{{{latex}}}"

    return re.sub(
        r'\\char\s*"\s*([0-9A-Fa-f]{3,4})',
        repl,
        s,
    )


def _fix_chi(s: str) -> str:
    s = re.sub(
        r"\\color\{red\}\\Chi\b",
        r"\\textcolor{red}{\\textsf{X}}",
        s,
    )
    s = re.sub(
        r"\\red\s*\\Chi\b",
        r"\\textcolor{red}{\\textsf{X}}",
        s,
    )
    s = re.sub(
        r"\\textcolor\{red\}\{\\Chi\}",
        r"\\textcolor{red}{\\textsf{X}}",
        s,
    )
    s = re.sub(r"\\Chi\b", r"\\mathrm{X}", s)
    return s


def _fix_text_and_texttt(s: str) -> str:
    # \\texttt0, \\texttt1, \\texttt X
    s = re.sub(
        r"\\texttt\s*([0-9A-Za-z])\b",
        r"\\texttt{\1}",
        s,
    )
    # \\text A, \\text E (single letter; often followed by _ or subscript)
    s = re.sub(
        r"\\text\s+([A-Za-z])(?=[^a-zA-Z]|_|$)",
        r"\\text{\1}",
        s,
    )
    # \\text\\{ → \\text{
    s = re.sub(r"\\text\\\{", r"\\text{", s)
    return s


def _fix_frac_and_font_aliases(s: str) -> str:
    s = re.sub(r"\\dfrac\b", r"\\frac", s)
    s = re.sub(r"\\tfrac\b", r"\\frac", s)
    s = re.sub(r"\\dbinom\b", r"\\binom", s)
    s = re.sub(r"\\tbinom\b", r"\\binom", s)
    s = re.sub(r"\\cfrac\b", r"\\frac", s)
    s = re.sub(r"\\boldcdot\b", r"\\cdot", s)
    s = re.sub(r"\\space\b", r"\\,", s)
    s = re.sub(r"\\nobreakspace\b", r"~", s)
    return s

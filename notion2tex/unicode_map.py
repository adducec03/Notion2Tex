"""
Unicode code points → LaTeX for pdfLaTeX (\\DeclareUnicodeCharacter).

Covers Greek letters, common math operators, and symbols found in Notion/KaTeX exports.
"""

from __future__ import annotations

# Lowercase Greek (U+03B1–U+03C9, plus variants)
_GREEK_LOWER: dict[str, str] = {
    "03B1": r"\alpha",
    "03B2": r"\beta",
    "03B3": r"\gamma",
    "03B4": r"\delta",
    "03B5": r"\varepsilon",
    "03B6": r"\zeta",
    "03B7": r"\eta",
    "03B8": r"\theta",
    "03B9": r"\iota",
    "03BA": r"\kappa",
    "03BB": r"\lambda",
    "03BC": r"\mu",
    "03BD": r"\nu",
    "03BE": r"\xi",
    "03BF": r"o",  # omicron (no \\omicron in standard LaTeX)
    "03C0": r"\pi",
    "03C1": r"\rho",
    "03C2": r"\varsigma",
    "03C3": r"\sigma",
    "03C4": r"\tau",
    "03C5": r"\upsilon",
    "03C6": r"\phi",
    "03C7": r"\chi",
    "03C8": r"\psi",
    "03C9": r"\omega",
    # Variant forms
    "03D1": r"\vartheta",
    "03D5": r"\varphi",
    "03D6": r"\varpi",
    "03F0": r"\varkappa",
    "03F1": r"\varrho",
    "03F5": r"\epsilon",
}

# Uppercase Greek: LaTeX commands where they exist, else \\mathrm{letter}
_GREEK_UPPER: dict[str, str] = {
    "0391": r"\mathrm{A}",
    "0392": r"\mathrm{B}",
    "0393": r"\Gamma",
    "0394": r"\Delta",
    "0395": r"\mathrm{E}",
    "0396": r"\mathrm{Z}",
    "0397": r"\mathrm{H}",
    "0398": r"\Theta",
    "0399": r"\mathrm{I}",
    "039A": r"\mathrm{K}",
    "039B": r"\Lambda",
    "039C": r"\mathrm{M}",
    "039D": r"\mathrm{N}",
    "039E": r"\Xi",
    "039F": r"\mathrm{O}",
    "03A0": r"\Pi",
    "03A1": r"\mathrm{P}",
    "03A3": r"\Sigma",
    "03A4": r"\mathrm{T}",
    "03A5": r"\Upsilon",
    "03A6": r"\Phi",
    "03A7": r"\mathrm{X}",
    "03A8": r"\Psi",
    "03A9": r"\Omega",
}

# Arrows, relations, set/logic, operators (common in CS / automata notes)
_MATH_SYMBOLS: dict[str, str] = {
    "00AC": r"\neg",
    "00B1": r"\pm",
    "00B7": r"\cdot",
    "00D7": r"\times",
    "00F7": r"\div",
    "00B5": r"\mu",  # micro sign (often used like μ)
    "2113": r"\ell",
    "2118": r"\wp",
    "2135": r"\aleph",
    "2136": r"\beth",
    "2115": r"\mathbb{N}",
    "211A": r"\mathbb{O}",
    "211D": r"\mathbb{R}",
    "2102": r"\mathbb{C}",
    "2124": r"\mathbb{Z}",
    "2119": r"\mathbb{P}",
    "2111": r"\mathbb{I}",
    "00B0": r"^{\circ}",
    "2190": r"\leftarrow",
    "2191": r"\uparrow",
    "2192": r"\rightarrow",
    "2193": r"\downarrow",
    "2194": r"\leftrightarrow",
    "21A6": r"\mapsto",
    "21D0": r"\Leftarrow",
    "21D2": r"\Rightarrow",
    "21D3": r"\Downarrow",
    "21D4": r"\Leftrightarrow",
    "2200": r"\forall",
    "2203": r"\exists",
    "2204": r"\nexists",
    "2205": r"\emptyset",
    "2206": r"\Delta",
    "2208": r"\in",
    "2209": r"\notin",
    "220B": r"\ni",
    "220C": r"\notni",
    "220F": r"\prod",
    "2211": r"\sum",
    "2212": r"-",
    "2213": r"\mp",
    "2216": r"\setminus",
    "2217": r"\ast",
    "2218": r"\circ",
    "2219": r"\bullet",
    "221A": r"\surd",
    "221D": r"\propto",
    "221E": r"\infty",
    "2223": r"\mid",
    "2224": r"\nmid",
    "2225": r"\parallel",
    "2226": r"\nparallel",
    "2227": r"\land",
    "2228": r"\lor",
    "2229": r"\cap",
    "222A": r"\cup",
    "222B": r"\int",
    "222E": r"\oint",
    "2234": r"\therefore",
    "2235": r"\because",
    "223C": r"\sim",
    "2240": r"\wr",
    "2243": r"\simeq",
    "2245": r"\cong",
    "2248": r"\approx",
    "2250": r"\doteq",
    "2260": r"\neq",
    "2261": r"\equiv",
    "2262": r"\not\equiv",
    "2264": r"\leq",
    "2265": r"\geq",
    "226A": r"\ll",
    "226B": r"\gg",
    "2282": r"\subset",
    "2283": r"\supset",
    "2284": r"\not\subset",
    "2286": r"\subseteq",
    "2287": r"\supseteq",
    "2288": r"\nsubseteq",
    "2289": r"\nsupseteq",
    "228A": r"\subsetneq",
    "228B": r"\supsetneq",
    "228E": r"\uplus",
    "2293": r"\sqcap",
    "2294": r"\sqcup",
    "2295": r"\oplus",
    "2296": r"\ominus",
    "2297": r"\otimes",
    "2298": r"\oslash",
    "2299": r"\odot",
    "22A2": r"\vdash",
    "22A3": r"\dashv",
    "22A8": r"\models",
    "22C0": r"\bigwedge",
    "22C1": r"\bigvee",
    "22C2": r"\bigcap",
    "22C3": r"\bigcup",
    "22C4": r"\diamond",
    "22C5": r"\cdot",
    "22C6": r"\star",
    "22C8": r"\bowtie",
    "22EE": r"\vdots",
    "22EF": r"\cdots",
    "22F1": r"\ddots",
    "2308": r"\lceil",
    "2309": r"\rceil",
    "230A": r"\lfloor",
    "230B": r"\rfloor",
    "2322": r"\frown",
    "2323": r"\smile",
    "25A1": r"\square",
    "25B3": r"\triangle",
    "25B5": r"\vartriangle",
    "25C6": r"\blacklozenge",
    "25CB": r"\circ",
    "25EF": r"\bigcirc",
    "2713": r"\checkmark",
    "2717": r"\times",
    # Box-drawing (Pandoc sometimes leaves these as raw Unicode)
    "251C": r"\vdash",
}

# Text mode / punctuation (outside \\ensuremath)
_TEXT_SYMBOLS: dict[str, str] = {
    "02CB": r"`",
    "2032": r"'",
    "2033": r"''",
    "203E": r"\textasciimacron",
    "2013": r"--",
    "2014": r"---",
    "2018": r"`",
    "2019": r"'",
    "201C": r"``",
    "201D": r"''",
    "2026": r"\ldots",
    "00A0": r"~",  # non-breaking space
}

UNICODE_MATH: dict[str, str] = {
    **_GREEK_LOWER,
    **_GREEK_UPPER,
    **_MATH_SYMBOLS,
}

UNICODE_TEXT: dict[str, str] = dict(_TEXT_SYMBOLS)

_UNICODE_MARKER = "% notion2tex: unicode declarations"


def unicode_preamble_lines() -> list[str]:
    """Lines to insert before \\begin{document}."""
    lines = [_UNICODE_MARKER]
    for code, cmd in sorted(UNICODE_MATH.items()):
        lines.append(
            f"\\DeclareUnicodeCharacter{{{code}}}{{\\ensuremath{{{cmd}}}}}"
        )
    for code, cmd in sorted(UNICODE_TEXT.items()):
        lines.append(f"\\DeclareUnicodeCharacter{{{code}}}{{{cmd}}}")
    return lines


def has_unicode_preamble(text: str) -> bool:
    return _UNICODE_MARKER in text


def latex_for_codepoint(hex_code: str) -> str | None:
    """Return LaTeX command for a 4-digit BMP hex code point, if known."""
    key = hex_code.upper().replace("0X", "")
    if len(key) > 4:
        return None
    key = key.zfill(4)
    return UNICODE_MATH.get(key) or UNICODE_TEXT.get(key)

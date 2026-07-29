from notion2tex.fix_latex import _ensure_strikeout_support

PANDOC_BLOCK = r"""
\ifLuaTeX
  \usepackage{luacolor}
  \usepackage[soul]{lua-ul}
\else
  \usepackage{soul}
\fi
"""


def test_strikeout_falls_back_when_soul_missing():
    fixed = _ensure_strikeout_support(PANDOC_BLOCK)
    assert r"\usepackage{soul}" not in fixed or "IfFileExists{soul.sty}" in fixed
    assert "IfFileExists{soul.sty}" in fixed
    assert "ulem" in fixed


def test_inserts_soul_fallback_when_pandoc_block_absent_but_ul_used():
    # Underline (\ul{}) comes from our own Lua filter as raw LaTeX, not from
    # a native Pandoc Strikeout AST node — so a doc using only underline
    # (no strikethrough) never gets Pandoc's own soul-loading block at all.
    text = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Chiamo \\ul{esiti} o \\ul{eventi} gli elementi di \\(\\Omega\\).\n"
        "\\end{document}\n"
    )
    fixed = _ensure_strikeout_support(text)
    assert "IfFileExists{soul.sty}" in fixed
    assert "ulem" in fixed
    assert fixed.index("IfFileExists{soul.sty}") < fixed.index(r"\begin{document}")


def test_leaves_text_alone_when_no_soul_macros_used():
    text = "\\documentclass{article}\n\\begin{document}\nplain text\n\\end{document}\n"
    assert _ensure_strikeout_support(text) == text


def test_does_not_duplicate_when_soul_already_loaded():
    text = (
        "\\documentclass{article}\n"
        "\\usepackage{soul}\n"
        "\\begin{document}\n"
        "\\ul{text}\n"
        "\\end{document}\n"
    )
    assert _ensure_strikeout_support(text) == text

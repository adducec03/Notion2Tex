from notion2tex.fix_latex import _ensure_code_wrapping

_WITH_CODE = (
    "\\begin{document}\n"
    "\\begin{Shaded}\n"
    "\\begin{Highlighting}[]\n"
    "\\NormalTok{x = 1}\n"
    "\\end{Highlighting}\n"
    "\\end{Shaded}\n"
    "\\end{document}\n"
)

_WITHOUT_CODE = "\\begin{document}\nJust text, no code blocks.\n\\end{document}\n"


def test_inserts_fvextra_when_code_block_present():
    out = _ensure_code_wrapping(_WITH_CODE)
    assert r"\usepackage{fvextra}" in out
    assert "breaklines=true,breakanywhere=true" in out
    assert r"\IfFileExists{fvextra.sty}" in out
    assert out.index(r"\IfFileExists{fvextra.sty}") < out.index(r"\begin{document}")


def test_noop_when_no_code_block():
    assert _ensure_code_wrapping(_WITHOUT_CODE) == _WITHOUT_CODE


def test_noop_when_fvextra_already_loaded():
    text = "\\usepackage{fvextra}\n" + _WITH_CODE
    assert _ensure_code_wrapping(text) == text


def test_idempotent():
    once = _ensure_code_wrapping(_WITH_CODE)
    assert _ensure_code_wrapping(once) == once

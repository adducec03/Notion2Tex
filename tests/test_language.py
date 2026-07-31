from notion2tex.fix_latex import _ensure_language_support

_TEXT = "\\documentclass{article}\n\\usepackage{xcolor}\n\\begin{document}\nHello\n\\end{document}\n"


def test_no_lang_leaves_text_unchanged():
    assert _ensure_language_support(_TEXT, None) == _TEXT


def test_italian_inserts_babel():
    out = _ensure_language_support(_TEXT, "it")
    assert r"\usepackage[italian]{babel}" in out
    assert out.index(r"\usepackage[italian]{babel}") < out.index(r"\begin{document}")


def test_english_inserts_babel():
    out = _ensure_language_support(_TEXT, "en")
    assert r"\usepackage[english]{babel}" in out


def test_idempotent():
    once = _ensure_language_support(_TEXT, "it")
    twice = _ensure_language_support(once, "it")
    assert once == twice
    assert twice.count(r"\usepackage[italian]{babel}") == 1

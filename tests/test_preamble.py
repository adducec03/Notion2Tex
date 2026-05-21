"""Tests for LaTeX preamble fixes."""

from notion2tex.fix_latex import _ensure_grffile, _fix_literal_backslash_n_in_preamble


def test_grffile_uses_real_newline():
    tex = r"\usepackage{graphicx}"
    out = _ensure_grffile(tex)
    assert "\\usepackage{graphicx}\n\\usepackage{grffile}" in out
    assert r"\n\\usepackage" not in out


def test_fix_literal_backslash_n():
    broken = r"\usepackage{graphicx}\n\usepackage{grffile}"
    fixed = _fix_literal_backslash_n_in_preamble(broken)
    assert r"\n\usepackage" not in fixed
    assert "\\usepackage{grffile}" in fixed

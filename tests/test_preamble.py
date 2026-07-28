"""Tests for LaTeX preamble fixes."""

from notion2tex.fix_latex import (
    _apply_dark_theme,
    _ensure_grffile,
    _fix_literal_backslash_n_in_preamble,
)


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


def test_apply_dark_theme():
    text = (
        "\\usepackage{xcolor}\n"
        "\\hypersetup{\n"
        "  colorlinks=true,\n"
        "  linkcolor=blue!70!black,\n"
        "  urlcolor=blue}\n"
        "\\fancyhead[C]{\\rightmark}\n"
        "\\fancyfoot[C]{\\thepage}\n"
        "\\begin{document}\n"
        "\\maketitle\n"
        "\\begin{table}[H]\n\\end{table}\n"
        "\\begin{figure}[H]\n\\end{figure}\n"
    )
    out = _apply_dark_theme(text)
    assert r"\pagecolor{notiondarkbg}" in out
    assert r"\color{notiondarktext}" in out
    assert "definecolor{notiondarkbg}{RGB}{30,30,30}" in out
    assert "linkcolor=blue!70!black" not in out
    assert "linkcolor=notiondarklink" in out
    assert out.index(r"\begin{document}") < out.index(r"\pagecolor{notiondarkbg}")

    # fancyhdr composes header/footer separately: needs an explicit color
    assert r"\fancyhead[C]{\color{notiondarktext}\rightmark}" in out
    assert r"\fancyfoot[C]{\color{notiondarktext}\thepage}" in out

    # floats (table/figure) are boxed separately too
    assert r"\begin{table}[H]\color{notiondarktext}" in out
    assert r"\begin{figure}[H]\color{notiondarktext}" in out

    # idempotent: running it twice does not duplicate the setup
    assert _apply_dark_theme(out) == out

"""Tests for includegraphics / image path fixes."""

from notion2tex.fix_latex import _deescape_pandoc_latex, _fix_figure_images


def test_deescape_includegraphics_not_split():
    raw = r"\textbackslash includegraphics[keepaspectratio]{foo/bar.png}"
    out = _deescape_pandoc_latex(raw)
    assert r"\includegraphics" in out
    assert r"\in cludegraphics" not in out


def test_fix_broken_includegraphics_and_href():
    tex = (
        r'\href{foo\%20bar.png}{\pandocbounded{\in cludegraphics[keepaspectratio]'
        r'{Automata, Languages and Computing/Screenshot_2025.png}}}'
    )
    out = _fix_figure_images(tex, "page.tex")
    assert r"\href" not in out
    assert "includegraphics" in out
    assert "width=" in out
    assert "Automata, Languages and Computing/Screenshot_2025.png" in out
    assert "in cludegraphics" not in out

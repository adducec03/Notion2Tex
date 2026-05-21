from notion2tex.fix_latex import _toc_insertion_point, _unnumbered_cover_section


def test_unnumbered_first_section():
    text = r"""
\begin{document}
\maketitle
\section{Economia applicata all'ingegneria}
\section{Microeconomia}
"""
    out = _unnumbered_cover_section(text)
    assert r"\section*{Economia" in out
    assert r"\section{Microeconomia}" in out


def test_toc_before_first_body_section():
    text = r"""
\begin{document}
\section*{Page Title}
\begin{table}...\end{table}
}
\section{Chapter One}
"""
    pos = _toc_insertion_point(text)
    assert pos is not None
    assert text[pos:].startswith(r"\section{Chapter One}")

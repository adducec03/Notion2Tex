"""Tests for KaTeX → LaTeX normalization."""

from notion2tex.katex_latex import normalize_katex


def test_exist_empty():
    assert r"\exists" in normalize_katex(r"\exist x")
    assert r"\emptyset" in normalize_katex(r"L=\empty")


def test_not_exist():
    assert normalize_katex(r"\not\exist c") == r"\nexists c"


def test_colors():
    assert normalize_katex(r"\red{A}") == r"\textcolor{red}{A}"
    assert normalize_katex(r"\green\checkmark") == r"\color{green}\checkmark"


def test_char_vdash():
    assert normalize_katex(r'\char"251C^*') == r"\ensuremath{\vdash}^*"


def test_texttt_unbraced():
    assert normalize_katex(r"\texttt0") == r"\texttt{0}"
    assert normalize_katex(r"\Sigma=\{\texttt0,\texttt1\}") == r"\Sigma=\{\texttt{0},\texttt{1}\}"


def test_text_unbraced():
    assert normalize_katex(r"\text A_\text{TM}") == r"\text{A}_\text{TM}"


def test_unicode_and_arrows():
    assert normalize_katex("n ≥ 0") == r"n \geq 0"
    assert normalize_katex("S→ S+S") == r"S\rightarrow S+S"


def test_bold_and_chi():
    assert normalize_katex(r"\bold \delta") == r"\boldsymbol \delta"
    assert normalize_katex(r"\red\Chi") == r"\textcolor{red}{\textsf{X}}"


def test_html_class_stripped():
    assert normalize_katex(r"\htmlClass{foo}{x+y}") == "x+y"


def test_operator_spacing():
    assert normalize_katex("|V'|≥K") == r"|V'|\geq K"
    assert normalize_katex(r"f:\mathbb N→P") == r"f:\mathbb N\rightarrow P"

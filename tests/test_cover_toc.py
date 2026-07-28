from notion2tex.fix_latex import (
    _add_roman_frontmatter_pagenumbering,
    _add_running_chapter_header,
    _add_table_of_contents,
    _ensure_arabic_mainmatter_pagenumbering,
    _start_chapters_on_new_page,
    _toc_insertion_point,
    _unnumbered_cover_section,
)


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


def test_roman_frontmatter_and_arabic_mainmatter():
    text = r"""
\begin{document}
\maketitle
\section*{Cover}
\newpage
\section*{Indice}
\tableofcontents
\newpage
\section{Chapter One}
"""
    text, n = _add_table_of_contents(text)
    assert n == 0
    assert r"\pagenumbering{roman}" in text
    assert text.index(r"\pagenumbering{roman}") < text.index(r"\tableofcontents")
    assert r"\pagenumbering{arabic}" in text
    assert text.index(r"\tableofcontents") < text.index(r"\pagenumbering{arabic}")
    assert text.index(r"\pagenumbering{arabic}") < text.index(r"\section{Chapter One}")


def test_inserts_toc_with_page_numbering():
    text = r"""
\begin{document}
\section*{Title}
\section{Body}
"""
    text, n = _add_table_of_contents(text)
    assert n == 1
    assert r"\pagenumbering{roman}" in text
    assert r"\section*{Indice}" in text
    assert r"\pagenumbering{arabic}" in text
    assert text.index(r"\pagenumbering{arabic}") < text.index(r"\section{Body}")


def test_start_chapters_on_new_page():
    text = (
        r"\section*{Cover}"
        "\ntext\n"
        r"\section{Chapter One}"
        "\nmore text\n"
        r"\section{Chapter Two}"
    )
    out = _start_chapters_on_new_page(text)
    assert out.count(r"\clearpage") == 2
    assert r"\clearpage" + "\n" + r"\section{Chapter One}" in out
    assert r"\clearpage" + "\n" + r"\section{Chapter Two}" in out
    # the cover's own \section* never gets a \clearpage in front of it
    assert r"\clearpage" + "\n" + r"\section*{Cover}" not in out


def test_add_running_chapter_header():
    text = "\\begin{document}\n\\section{Chapter One}\n"
    out = _add_running_chapter_header(text)
    assert r"\usepackage{fancyhdr}" in out
    assert r"\pagestyle{fancy}" in out
    assert r"\fancyhead[C]{\rightmark}" in out
    assert r"\renewcommand{\sectionmark}[1]{\markright{#1}}" in out
    assert r"\renewcommand{\subsectionmark}[1]{}" in out
    assert out.index(r"\usepackage{fancyhdr}") < out.index(r"\begin{document}")

    # idempotent: running it twice does not duplicate the header setup
    assert _add_running_chapter_header(out) == out

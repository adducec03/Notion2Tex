from bs4 import BeautifulSoup

from notion2tex.clean_html import _unwrap_toggle_lists
from notion2tex.fix_latex import _unwrap_paragraph_itemize


def test_unwrap_toggle_lists_removes_ul_wrapper():
    html = """
    <ul class="toggle"><li>
    <h4>Volume di Pareggio</h4>
    <p>Break-even text.</p>
    <ul class="bulleted-list"><li>nested item</li></ul>
    </li></ul>
    """
    soup = BeautifulSoup(html, "html.parser")
    assert _unwrap_toggle_lists(soup) == 1
    assert soup.find("ul", class_="toggle") is None
    h4 = soup.find("h4")
    assert h4 and h4.get_text(strip=True) == "Volume di Pareggio"
    assert h4.find_next("p").get_text(strip=True).startswith("Break-even")


def test_unwrap_paragraph_itemize_in_latex():
    tex = r"""
\begin{itemize}
\item ~
  \paragraph{Volume di Pareggio}\label{vol}

  Some text here.

  \begin{itemize}
  \item nested
  \end{itemize}
\end{itemize}
"""
    fixed, n = _unwrap_paragraph_itemize(tex)
    assert n == 1
    assert r"\item ~" not in fixed
    assert r"\paragraph{Volume di Pareggio}" in fixed
    assert r"\begin{itemize}" in fixed  # nested list kept
    assert fixed.index(r"\paragraph{Volume") < fixed.index("Some text")


def test_unwrap_subparagraph_itemize_with_indent():
    tex = r"""
  \begin{itemize}
  \item ~
    \subparagraph{Variazione del reddito}\label{var}

    Body text.
  \end{itemize}
"""
    fixed, n = _unwrap_paragraph_itemize(tex)
    assert n == 1
    assert r"\item ~" not in fixed
    assert r"\subparagraph{Variazione del reddito}" in fixed

"""End-to-end check that `book=False` (the default) produces a minimal
document, while `book=True` preserves the previous always-on behavior
(cover page, table of contents, per-chapter page breaks, running header).
"""

from pathlib import Path

from notion2tex.fix_latex import fix_latex

_FIXTURE = r"""\documentclass[11pt]{article}
\usepackage{xcolor}
\usepackage[hidelinks]{hyperref}
\usepackage{graphicx}
\usepackage{cancel}
\setcounter{secnumdepth}{0} %no-numbers
\begin{document}
\maketitle

\includegraphics[width=\linewidth,keepaspectratio]{cover.jpg}

\section{Test Page}\label{test-page}

Some body text \(x=1\).

\section{Second Chapter}\label{second-chapter}

More text here.
\end{document}
"""


def _write_fixture(tmp_path: Path) -> Path:
    tex = tmp_path / "doc.tex"
    tex.write_text(_FIXTURE, encoding="utf-8")
    # _fix_figure_images only keeps \includegraphics pointing at a file that
    # actually exists on disk; _build_cover_page needs that image intact.
    (tmp_path / "cover.jpg").write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")
    return tex


def test_default_is_minimal_no_book_features(tmp_path: Path):
    tex = _write_fixture(tmp_path)
    fix_latex(str(tex))
    out = tex.read_text(encoding="utf-8")

    assert r"\maketitle" not in out
    assert r"\tableofcontents" not in out
    assert r"\usepackage{fancyhdr}" not in out
    assert r"\clearpage" not in out
    assert r"\pagenumbering{roman}" not in out
    # content itself is untouched
    assert "Test Page" in out
    assert "Second Chapter" in out
    assert "Some body text" in out


def test_book_true_preserves_existing_behavior(tmp_path: Path):
    tex = _write_fixture(tmp_path)
    fix_latex(str(tex), book=True)
    out = tex.read_text(encoding="utf-8")

    assert r"\maketitle" not in out  # merged into the designed cover page
    assert r"\tableofcontents" in out
    assert r"\usepackage{fancyhdr}" in out
    assert r"\clearpage" in out
    assert r"\pagenumbering{roman}" in out
    assert r"\pagenumbering{arabic}" in out
    assert "Test Page" in out
    assert "Second Chapter" in out

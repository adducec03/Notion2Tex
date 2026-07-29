from notion2tex.fix_latex import (
    _strip_blank_lines_in_math_environments,
    _unwrap_align_inside_gathered,
)


def test_unwraps_align_star_nested_in_gathered():
    text = (
        "Some text.\n\n"
        r"\[\begin{gathered}"
        "\n"
        r"\begin{align*}"
        "\n"
        r"\mathbb P (E\cup E^C)=\mathbb P(E)+\mathbb P(E^C) &&&& \text{(ass. 3)}\\"
        "\n"
        r"E\cup E^C=\Omega\\"
        "\n"
        r"\mathbb P(E\cup E^C)=1 &&&& \text{(ass. 2)}\\"
        "\n"
        r"\end{align*}"
        "\n"
        r"\end{gathered}\]"
        "\n\nMore text."
    )
    out = _unwrap_align_inside_gathered(text)
    assert r"\begin{gathered}" not in out
    assert r"\end{gathered}" not in out
    assert r"\[\begin{align*}" not in out
    assert out.count(r"\begin{align*}") == 1
    assert out.count(r"\end{align*}") == 1
    assert "Some text." in out and "More text." in out


def test_leaves_plain_gathered_untouched():
    text = (
        r"\[\begin{gathered}"
        "\n"
        r"a=b\\"
        "\n"
        r"c=d"
        "\n"
        r"\end{gathered}\]"
    )
    out = _unwrap_align_inside_gathered(text)
    assert out == text


def test_leaves_aligned_inside_gathered_untouched():
    # `aligned` (unlike `align*`) is a nestable building-block environment,
    # not a top-level display-math starter, so this pattern is valid as-is.
    text = (
        r"\[\begin{gathered}"
        "\n"
        r"\begin{aligned}a &= b\\ c&=d\end{aligned}"
        "\n"
        r"\end{gathered}\]"
    )
    out = _unwrap_align_inside_gathered(text)
    assert out == text


def test_idempotent():
    text = (
        r"\[\begin{gathered}"
        "\n"
        r"\begin{align*}a &= b\end{align*}"
        "\n"
        r"\end{gathered}\]"
    )
    once = _unwrap_align_inside_gathered(text)
    assert _unwrap_align_inside_gathered(once) == once


def test_strips_blank_line_inside_gathered():
    # A blank line inside `gathered` becomes \par at typeset time, which is
    # illegal in math mode ("Missing $ inserted", cascading into dozens of
    # unrelated errors through the rest of the document).
    text = (
        r"\[\begin{gathered}"
        "\n"
        r"p(2)=\frac{1}{36}\quad p(3)=\frac{2}{36}\\"
        "\n"
        "\n"
        r"p(7)=\frac{6}{36}\quad p(8)=\frac{5}{36}\\"
        "\n"
        r"p(12)=\frac{1}{36}"
        "\n"
        r"\end{gathered}\]"
    )
    out = _strip_blank_lines_in_math_environments(text)
    body = out[out.index(r"\begin{gathered}") : out.index(r"\end{gathered}")]
    assert "\n\n" not in body
    assert r"p(2)=\frac{1}{36}" in out and r"p(12)=\frac{1}{36}" in out


def test_strips_blank_line_inside_align_star():
    text = (
        r"\begin{align*}"
        "\n"
        r"a &= b\\"
        "\n"
        "\n"
        r"c &= d"
        "\n"
        r"\end{align*}"
    )
    out = _strip_blank_lines_in_math_environments(text)
    assert "\n\n" not in out


def test_leaves_text_outside_math_environments_untouched():
    text = "Paragraph one.\n\nParagraph two.\n\n\\begin{align*}a=b\\end{align*}"
    out = _strip_blank_lines_in_math_environments(text)
    assert "Paragraph one.\n\nParagraph two." in out


def test_strip_blank_lines_idempotent():
    text = (
        r"\begin{gathered}a=b\\"
        "\n\n"
        r"c=d\end{gathered}"
    )
    once = _strip_blank_lines_in_math_environments(text)
    assert _strip_blank_lines_in_math_environments(once) == once

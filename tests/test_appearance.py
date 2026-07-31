from notion2tex.fix_latex import (
    _apply_accent_color,
    _apply_font,
    _apply_font_size,
    _ensure_page_geometry,
)

_PREAMBLE = (
    "\\documentclass[\n]{article}\n"
    "\\usepackage{xcolor}\n"
    "\\usepackage{lmodern}\n"
    "\\begin{document}\n"
    "Hello\n"
    "\\end{document}\n"
)


def test_apply_font_none_is_noop():
    assert _apply_font(_PREAMBLE, None) == _PREAMBLE


def test_apply_font_serif_layers_mathptmx_after_lmodern():
    out = _apply_font(_PREAMBLE, "serif")
    assert r"\usepackage{mathptmx}" in out
    assert out.index(r"\usepackage{lmodern}") < out.index(r"\usepackage{mathptmx}")


def test_apply_font_sans_switches_family_default():
    out = _apply_font(_PREAMBLE, "sans")
    assert r"\usepackage[scaled]{helvet}" in out
    assert r"\renewcommand{\familydefault}{\sfdefault}" in out


def test_apply_font_idempotent():
    once = _apply_font(_PREAMBLE, "serif")
    assert _apply_font(once, "serif") == once


def test_apply_font_size_none_is_noop():
    assert _apply_font_size(_PREAMBLE, None) == _PREAMBLE


def test_apply_font_size_inserts_into_empty_options():
    out = _apply_font_size(_PREAMBLE, "12")
    assert r"\documentclass[12pt]{article}" in out


def test_apply_font_size_appends_to_existing_options():
    text = "\\documentclass[twocolumn]{article}\n\\begin{document}\n\\end{document}\n"
    out = _apply_font_size(text, "11")
    assert r"\documentclass[twocolumn,11pt]{article}" in out


def test_geometry_defaults_to_a4_normal_when_unset():
    out = _ensure_page_geometry(_PREAMBLE, None, None)
    assert r"\usepackage[a4paper,margin=1in]{geometry}" in out


def test_geometry_respects_explicit_paper_and_margins():
    out = _ensure_page_geometry(_PREAMBLE, "letter", "wide")
    assert r"\usepackage[letterpaper,margin=1.5in]{geometry}" in out


def test_geometry_narrow_margin():
    out = _ensure_page_geometry(_PREAMBLE, "a4", "narrow")
    assert r"\usepackage[a4paper,margin=0.75in]{geometry}" in out


def test_geometry_idempotent_when_already_present():
    text = _PREAMBLE.replace(
        r"\begin{document}",
        "\\usepackage[letterpaper,margin=2in]{geometry}\n\\begin{document}",
    )
    assert _ensure_page_geometry(text, "a4", "narrow") == text


def test_accent_color_none_is_noop():
    text = _PREAMBLE.replace(
        r"\usepackage{xcolor}",
        "\\usepackage{xcolor}\n\\usepackage[hidelinks]{hyperref}",
    )
    assert _apply_accent_color(text, None) == text


def test_accent_color_overrides_light_mode_link_color():
    text = _PREAMBLE.replace(
        r"\usepackage{xcolor}",
        "\\usepackage{xcolor}\n"
        "\\hypersetup{\n  colorlinks=true,\n  linkcolor=blue!70!black,\n  urlcolor=blue}",
    )
    out = _apply_accent_color(text, "2E86AB")
    assert r"\definecolor{notionaccent}{HTML}{2E86AB}" in out
    assert "linkcolor=notionaccent" in out
    assert "urlcolor=notionaccent" in out
    assert "linkcolor=blue!70!black" not in out


def test_accent_color_overrides_dark_mode_link_color():
    text = _PREAMBLE.replace(
        r"\usepackage{xcolor}",
        "\\usepackage{xcolor}\n"
        "\\hypersetup{\n  colorlinks=true,\n  linkcolor=notiondarklink,\n  urlcolor=notiondarklink}",
    )
    out = _apply_accent_color(text, "2E86AB")
    assert "linkcolor=notionaccent" in out
    assert "linkcolor=notiondarklink" not in out


def test_accent_color_idempotent():
    text = _PREAMBLE.replace(
        r"\usepackage{xcolor}",
        "\\usepackage{xcolor}\n"
        "\\hypersetup{\n  colorlinks=true,\n  linkcolor=blue!70!black,\n  urlcolor=blue}",
    )
    once = _apply_accent_color(text, "2E86AB")
    assert _apply_accent_color(once, "2E86AB") == once

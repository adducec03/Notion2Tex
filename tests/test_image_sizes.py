"""Tests for Notion image width preservation."""

from pathlib import Path

from notion2tex.image_sizes import (
    LARGE_IMAGE_FRAC_THRESHOLD,
    apply_notion_image_sizes,
    apply_widths_to_includegraphics,
    load_image_width_map,
    unwrap_href_includegraphics,
    _normalize_graphics_options,
    _width_option_for_fraction,
)
from bs4 import BeautifulSoup


def test_apply_notion_image_sizes():
    soup = BeautifulSoup(
        '<img src="a/x.png" style="width:336px"/>',
        "html.parser",
    )
    assert apply_notion_image_sizes(soup) == 1
    img = soup.find("img")
    assert img["width"] == "336"
    assert img["data-notion-width-px"] == "336.0"


def test_load_and_apply_widths(tmp_path: Path):
    html = tmp_path / "page_clean.html"
    html.write_text(
        '<img src="Folder/img.png" style="width:450px"/>',
        encoding="utf-8",
    )
    widths = load_image_width_map(html)
    assert abs(widths["Folder/img.png"] - 0.5) < 0.01

    tex = r'\includegraphics[keepaspectratio]{"Folder/img.png"}'
    out = apply_widths_to_includegraphics(tex, widths)
    assert r"width=0.5000\linewidth" in out
    assert "keepaspectratio" in out


def test_large_image_capped_to_linewidth():
    assert _width_option_for_fraction(LARGE_IMAGE_FRAC_THRESHOLD) == r"width=\linewidth"
    assert _width_option_for_fraction(0.9) == r"width=\linewidth"
    assert "width=0.3000" in _width_option_for_fraction(0.3)


def test_replace_pandoc_inch_width():
    opts = r"[width=8.23958in,height=\textheight,keepaspectratio]"
    out = _normalize_graphics_options(opts, 0.5)
    assert r"width=0.5000\linewidth" in out
    assert "8.23958in" not in out
    assert "textheight" not in out


def test_center_figure_images():
    from notion2tex.image_sizes import center_figure_images

    tex = r"\begin{figure}[H]\raggedright\noindent\includegraphics{x}"
    out = center_figure_images(tex)
    assert r"\centering" in out
    assert r"\raggedright" not in out


def test_unwrap_href():
    tex = (
        r'\href{path.png}{\includegraphics[width=8in]'
        r'{"Automata, Languages and Computing/x.png"}}'
    )
    out = unwrap_href_includegraphics(tex)
    assert r"\href" not in out
    assert r'\includegraphics' in out


def test_large_px_uses_linewidth_in_tex(tmp_path: Path):
    html = tmp_path / "page_clean.html"
    html.write_text(
        '<img src="big.png" style="width:800px"/>',
        encoding="utf-8",
    )
    widths = load_image_width_map(html)
    tex = r'\includegraphics{"big.png"}'
    out = apply_widths_to_includegraphics(tex, widths)
    assert r"width=\linewidth" in out

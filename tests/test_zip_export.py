"""Tests for Notion ZIP export extraction."""

import zipfile
from pathlib import Path

from notion2tex.zip_export import _extract_nested_zips, find_main_html


def test_extract_nested_zip(tmp_path: Path):
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / "page.html").write_text("<html></html>", encoding="utf-8")
    (inner / "page").mkdir()
    (inner / "page" / "img.png").write_bytes(b"x")

    nested_zip = tmp_path / "Part-1.zip"
    with zipfile.ZipFile(nested_zip, "w") as zf:
        zf.writestr("inner/page.html", "<html></html>")
        zf.writestr("inner/page/img.png", "x")

    outer = tmp_path / "outer"
    outer.mkdir()
    nested_zip.rename(outer / "ExportBlock-Part-1.zip")

    _extract_nested_zips(outer)
    assert not list(outer.rglob("*.zip"))
    html = find_main_html(outer)
    assert html.name == "page.html"


def test_notion_title_id_html(tmp_path: Path):
    root = tmp_path / "Private & Shared"
    root.mkdir()
    (root / "My Page").mkdir()
    (root / "My Page" / "a.png").write_bytes(b"1")
    (root / "My Page abc123deadbeef.html").write_text("<html></html>", encoding="utf-8")
    html = find_main_html(tmp_path)
    assert "My Page" in html.name

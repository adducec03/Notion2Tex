"""--offline must skip remote image downloads entirely (no network calls)."""

from pathlib import Path
from unittest.mock import patch

from notion2tex.clean_html import clean_html_for_pandoc

_HTML = (
    '<html><head><meta charset="utf-8"><title>Test</title></head>'
    "<body><article>"
    '<img class="page-cover-image" src="https://example.com/cover.jpg"/>'
    '<h1 class="page-title">Test</h1>'
    '<div class="page-body"><p>Hello.</p></div>'
    "</article></body></html>"
)


def _write_html(tmp_path: Path) -> Path:
    html = tmp_path / "page.html"
    html.write_text(_HTML, encoding="utf-8")
    return html


def test_offline_skips_remote_image_download(tmp_path: Path):
    html = _write_html(tmp_path)
    out = tmp_path / "page_clean.html"
    with patch("notion2tex.clean_html.download_remote_images") as mock_dl:
        clean_html_for_pandoc(str(html), str(out), offline=True)
    mock_dl.assert_not_called()


def test_default_still_calls_remote_image_download(tmp_path: Path):
    html = _write_html(tmp_path)
    out = tmp_path / "page_clean.html"
    with patch(
        "notion2tex.clean_html.download_remote_images", return_value=0
    ) as mock_dl:
        clean_html_for_pandoc(str(html), str(out))
    mock_dl.assert_called_once()

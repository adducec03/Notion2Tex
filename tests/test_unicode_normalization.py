"""Some sources leave accented characters Unicode-decomposed (e.g. "e" +
a standalone combining grave accent instead of precomposed "è"). LaTeX has
no definition for a bare combining accent and drops it, so the pipeline
folds the whole document to NFC before anything else touches it.
"""

import unicodedata
from pathlib import Path
from unittest.mock import patch

from notion2tex.clean_html import clean_html_for_pandoc

_DECOMPOSED_E = "è"  # "e" + combining grave accent (U+0300), not "è"
assert _DECOMPOSED_E != "è"
assert unicodedata.normalize("NFC", _DECOMPOSED_E) == "è"

_HTML = (
    '<html><head><meta charset="utf-8"><title>Test</title></head>'
    "<body><article>"
    '<h1 class="page-title">Test</h1>'
    f'<div class="page-body"><p>Non {_DECOMPOSED_E} uno stato finale.</p></div>'
    "</article></body></html>"
)


def test_decomposed_accents_are_folded_to_precomposed_form(tmp_path: Path):
    html = tmp_path / "page.html"
    html.write_text(_HTML, encoding="utf-8")
    out = tmp_path / "page_clean.html"

    with patch("notion2tex.clean_html.download_remote_images", return_value=0):
        clean_html_for_pandoc(str(html), str(out), offline=True)

    cleaned = out.read_text(encoding="utf-8")
    assert "è" in cleaned
    assert _DECOMPOSED_E not in cleaned

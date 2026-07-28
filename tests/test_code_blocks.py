from bs4 import BeautifulSoup

from notion2tex.clean_html import _fix_code_block_language


def test_strips_language_prefix_for_pandoc_highlighting():
    soup = BeautifulSoup(
        '<pre><code class="language-python">import os</code></pre>',
        "html.parser",
    )
    count = _fix_code_block_language(soup)
    assert count == 1
    assert soup.find("code")["class"] == ["python"]


def test_leaves_code_without_language_untouched():
    soup = BeautifulSoup("<pre><code>plain text</code></pre>", "html.parser")
    count = _fix_code_block_language(soup)
    assert count == 0
    assert soup.find("code").get("class") is None


def test_keeps_other_classes_alongside_language():
    soup = BeautifulSoup(
        '<code class="language-javascript inline">x</code>', "html.parser"
    )
    _fix_code_block_language(soup)
    assert soup.find("code")["class"] == ["javascript", "inline"]


def test_strips_pre_attributes_that_break_pandoc_highlighting():
    soup = BeautifulSoup(
        '<pre class="code code-wrap" data-notion-code-syntax="python">'
        '<code class="language-python" style="white-space:pre-wrap">x</code>'
        "</pre>",
        "html.parser",
    )
    _fix_code_block_language(soup)
    pre = soup.find("pre")
    assert pre.attrs == {}
    assert soup.find("code")["class"] == ["python"]
    # <code>'s own attributes (e.g. the inline style) are untouched
    assert soup.find("code")["style"] == "white-space:pre-wrap"

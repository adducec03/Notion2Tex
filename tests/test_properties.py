from bs4 import BeautifulSoup

from notion2tex.properties import normalize_properties_table
from notion2tex.table_latex import improve_longtable_block


def test_normalize_properties_removes_table():
    html = """
    <table class="properties"><tbody>
    <tr class="property-row property-row-url"><th><span class="icon property-icon"><img src="x.svg"/></span>Sito web</th>
    <td><a href="https://example.com" class="url-value">https://example.com</a></td></tr>
    <tr class="property-row property-row-text"><th><span class="icon property-icon"><img src="y.svg"/></span>Username</th>
    <td><span class="text-value">student123</span></td></tr>
    <tr class="property-row property-row-text"><th>Password</th>
    <td><span class="text-value">secret</span></td></tr>
    <tr class="property-row property-row-status"><th>Status</th>
    <td><span class="status-value"><div class="status-dot"></div>Done</span></td></tr>
    </tbody></table>
    """
    soup = BeautifulSoup(html, "html.parser")
    count, labels = normalize_properties_table(soup)
    assert count == 4
    assert labels == ["Sito web", "Username", "Password", "Status"]
    assert soup.find("table", class_="properties") is None


def test_key_value_longtable_rebuild():
    block = r"""
\begin{longtable}[]{@{}ll@{}}
\toprule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
{}Sito web & \url{https://example.com} \\
{}Username & student123 \\
{}Password & secret \\
{}Status & Done \\
\end{longtable}
"""
    new_block, ok = improve_longtable_block(block)
    assert ok
    assert r"\begin{tabular}" in new_block
    assert r"\textbf{Sito web}" in new_block
    assert r"\textbf{Username}" in new_block
    assert "student123" in new_block
    assert "secret" in new_block
    assert r"\midrule" not in new_block  # no header/body split

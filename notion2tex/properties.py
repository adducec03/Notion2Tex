"""Normalize Notion page property tables (cover metadata) for Pandoc/LaTeX."""

from bs4 import BeautifulSoup


def _clean_text(text):
    return " ".join(text.split())


def _normalize_property_cell(td):
    """Keep links and values; drop decorative UI (status dots, empty wrappers)."""
    for dot in td.select(".status-dot"):
        dot.decompose()
    for tag in td.find_all(["style", "script"]):
        tag.decompose()
    for div in td.find_all("div"):
        if not div.get_text(strip=True) and not div.find("a"):
            div.decompose()


def normalize_properties_table(soup):
    """
    Flatten Notion's properties table so every database field row is preserved.

    Returns (row_count, labels) for logging.
    """
    table = soup.find("table", class_="properties")
    if not table:
        return 0, []

    labels = []
    for tr in table.find_all("tr", class_=lambda c: c and "property-row" in c):
        th = tr.find("th")
        td = tr.find("td")
        if not th:
            continue
        for el in th.select(".property-icon, .icon, img"):
            el.decompose()
        label = _clean_text(th.get_text())
        th.clear()
        th.append(label)
        labels.append(label)
        if td:
            _normalize_property_cell(td)

    return len(labels), labels

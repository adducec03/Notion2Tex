"""Strip Notion page property tables (cover metadata) before Pandoc/LaTeX."""

from bs4 import BeautifulSoup


def _clean_text(text):
    return " ".join(text.split())


def normalize_properties_table(soup):
    """
    Remove Notion's properties table (site/username/password/... database
    fields shown under the cover) entirely — it's not meant to end up in the
    generated PDF.

    Returns (row_count, labels) of what was removed, for logging.
    """
    table = soup.find("table", class_="properties")
    if not table:
        return 0, []

    labels = []
    for tr in table.find_all("tr", class_=lambda c: c and "property-row" in c):
        th = tr.find("th")
        if not th:
            continue
        for el in th.select(".property-icon, .icon, img"):
            el.decompose()
        labels.append(_clean_text(th.get_text()))

    table.decompose()
    return len(labels), labels

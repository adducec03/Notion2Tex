"""Extract Notion HTML exports from ZIP archives."""

from __future__ import annotations

import zipfile
from pathlib import Path


def extract_zip(zip_path: str | Path, dest_dir: str | Path | None = None) -> Path:
    """Extract *zip_path* and return the directory used as export root."""
    zip_path = Path(zip_path).expanduser().resolve()
    if not zip_path.is_file():
        raise FileNotFoundError(f"ZIP file not found: {zip_path}")

    if dest_dir is None:
        dest_dir = zip_path.with_suffix("")
    else:
        dest_dir = Path(dest_dir).expanduser().resolve()

    dest_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)

    return _notion_export_root(dest_dir)


def _notion_export_root(extract_dir: Path) -> Path:
    """Descend into a single top-level folder (common Notion ZIP layout)."""
    entries = [
        p
        for p in extract_dir.iterdir()
        if p.name not in ("__MACOSX",) and not p.name.startswith(".")
    ]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return extract_dir


def find_main_html(root: Path) -> Path:
    """
    Pick the main Notion page HTML.

    Prefers an ``.html`` file that has a sibling directory with the same stem
    (the asset folder Notion creates alongside the page).
    """
    root = root.resolve()
    html_files = sorted(root.rglob("*.html"))
    if not html_files:
        raise FileNotFoundError(f"No .html file found under: {root}")

    def rank(html: Path) -> tuple[bool, int]:
        assets = html.parent / html.stem
        return assets.is_dir(), html.stat().st_size

    return max(html_files, key=rank)


def resolve_input(
    path: str | Path,
    *,
    extract_dir: Path | None = None,
) -> Path:
    """Return the main ``.html`` path from a Notion export ``.zip`` or ``.html`` file."""
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Input not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".zip":
        print(f"==> Extract ZIP → {extract_dir or path.with_suffix('')}")
        root = extract_zip(path, extract_dir)
        html = find_main_html(root)
        print(f"==> Main page: {html.name}")
        return html

    if suffix in (".html", ".htm"):
        return path

    raise ValueError(
        f"Unsupported input type: {path.name}. "
        "Use a Notion export .zip or .html file."
    )

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

    _extract_nested_zips(dest_dir)
    return _notion_export_root(dest_dir)


def _extract_nested_zips(directory: Path) -> None:
    """
    Notion large exports ship as ExportBlock-…-Part-N.zip inside the outer archive.
    Extract every nested .zip until the tree contains the HTML export.
    """
    directory = directory.resolve()
    while True:
        nested = [
            p
            for p in directory.rglob("*.zip")
            if p.is_file() and "__MACOSX" not in p.parts
        ]
        if not nested:
            return
        for part_zip in nested:
            print(f"==> Extract nested ZIP: {part_zip.name}")
            with zipfile.ZipFile(part_zip) as zf:
                zf.extractall(part_zip.parent)
            part_zip.unlink()


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


def _has_asset_folder(html: Path) -> bool:
    """True if the HTML has a Notion asset directory (images, etc.)."""
    parent = html.parent
    stem = html.stem
    if (parent / stem).is_dir():
        return True
    # Notion: "Page Title <page-id>.html" with folder "Page Title/"
    for child in parent.iterdir():
        if child.is_dir() and stem.startswith(child.name):
            return True
    return False


def find_main_html(root: Path) -> Path:
    """
    Pick the main Notion page HTML.

    Prefers the largest ``.html`` that has a matching asset folder (same stem,
    or Notion's ``Title/`` + ``Title <id>.html`` layout).
    """
    root = root.resolve()
    html_files = sorted(root.rglob("*.html"))
    if not html_files:
        raise FileNotFoundError(f"No .html file found under: {root}")

    def rank(html: Path) -> tuple[bool, int]:
        return _has_asset_folder(html), html.stat().st_size

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

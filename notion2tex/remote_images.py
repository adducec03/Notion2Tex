"""Download externally-hosted images (Notion page covers, link images, bookmark
previews) so pdflatex can embed them like any other local asset.

pdflatex has no network access, so an <img src="https://..."> left as-is
fails to compile. Failures here (network down, 404, non-image response) are
swallowed: the <img> src is left pointing at the remote URL, and downstream
\\includegraphics resolution (image_paths.py) omits it cleanly instead of
emitting a path pdflatex can never find.
"""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from notion2tex.console import console

DOWNLOAD_DIR_NAME = "notion2tex_downloads"
_TIMEOUT_SECONDS = 8.0
_USER_AGENT = "Mozilla/5.0 (compatible; notion2tex)"

# Extensions pdflatex/image_paths.py can actually embed (directly, or via the
# AVIF/WebP -> PNG conversion step). Anything else is as good as no file.
_EMBEDDABLE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".avif", ".webp"}

_CONTENT_TYPE_SUFFIXES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/webp": ".webp",
    "image/avif": ".avif",
}


def _is_remote_url(src: str) -> bool:
    return src.startswith("http://") or src.startswith("https://")


def _url_hash(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _suffix_for_download(url: str, content_type: str) -> str | None:
    """
    Pick a real image extension pdflatex/graphicx will recognize.

    Many CDNs (Unsplash included, used for Notion page covers) serve images
    from URLs with no file extension at all — deriving the local filename's
    suffix from the URL path alone previously produced a bogus ".img"
    extension that pdflatex's \\includegraphics silently can't embed, so the
    image got dropped as "unsupported format" even though the download had
    actually succeeded. Prefer the real Content-Type the server returned;
    fall back to the URL's own extension only if that header is missing or
    unrecognized.
    """
    main_type = content_type.split(";", 1)[0].strip().lower()
    suffix = _CONTENT_TYPE_SUFFIXES.get(main_type)
    if suffix:
        return suffix
    url_suffix = Path(urlparse(url).path).suffix.lower()
    if url_suffix in _EMBEDDABLE_SUFFIXES:
        return url_suffix
    return None


def _existing_download(dest_dir: Path, url: str) -> Path | None:
    if not dest_dir.is_dir():
        return None
    matches = sorted(dest_dir.glob(f"remote-{_url_hash(url)}.*"))
    return matches[0] if matches else None


def _download(url: str, dest_dir: Path) -> Path | None:
    cached = _existing_download(dest_dir, url)
    if cached is not None:
        return cached

    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            content_type = response.headers.get("Content-Type", "")
            if content_type and not content_type.startswith("image/"):
                return None
            data = response.read()
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    suffix = _suffix_for_download(url, content_type)
    if suffix is None:
        return None

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"remote-{_url_hash(url)}{suffix}"
    dest.write_bytes(data)
    return dest


def download_remote_images(soup, work_dir: Path) -> int:
    """
    Replace every <img src="http(s)://..."> with a local downloaded copy.

    Returns the number of images successfully downloaded and rewritten.
    """
    count = 0
    dest_dir = work_dir / DOWNLOAD_DIR_NAME
    for img in soup.find_all("img"):
        src = (img.get("src") or "").strip()
        if not _is_remote_url(src):
            continue

        dest = _download(src, dest_dir)
        if dest is not None:
            img["src"] = f"{DOWNLOAD_DIR_NAME}/{dest.name}"
            count += 1
        else:
            console.detail(f"Could not download image, omitting: {src}")

    return count

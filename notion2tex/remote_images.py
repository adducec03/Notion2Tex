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


def _is_remote_url(src: str) -> bool:
    return src.startswith("http://") or src.startswith("https://")


def _local_filename_for_url(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix
    if not suffix or len(suffix) > 6:
        suffix = ".img"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return f"remote-{digest}{suffix}"


def _download(url: str, dest: Path) -> bool:
    if dest.is_file():
        return True
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            content_type = response.headers.get("Content-Type", "")
            if content_type and not content_type.startswith("image/"):
                return False
            data = response.read()
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return True


def download_remote_images(soup, work_dir: Path) -> int:
    """
    Replace every <img src="http(s)://..."> with a local downloaded copy.

    Returns the number of images successfully downloaded and rewritten.
    """
    count = 0
    for img in soup.find_all("img"):
        src = (img.get("src") or "").strip()
        if not _is_remote_url(src):
            continue

        dest = work_dir / DOWNLOAD_DIR_NAME / _local_filename_for_url(src)
        if _download(src, dest):
            img["src"] = f"{DOWNLOAD_DIR_NAME}/{dest.name}"
            count += 1
        else:
            console.detail(f"Could not download image, omitting: {src}")

    return count

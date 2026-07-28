"""Tests for downloading externally-hosted images."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from notion2tex.remote_images import DOWNLOAD_DIR_NAME, download_remote_images


def _mock_response(body: bytes, content_type: str = "image/png"):
    response = MagicMock()
    response.__enter__.return_value = response
    response.headers = {"Content-Type": content_type}
    response.read.return_value = body
    return response


def test_download_remote_images_success(tmp_path: Path):
    soup = BeautifulSoup(
        '<img src="https://example.com/photo.jpg"/>', "html.parser"
    )
    with patch("urllib.request.urlopen", return_value=_mock_response(b"fake-bytes")):
        count = download_remote_images(soup, tmp_path)

    assert count == 1
    img = soup.find("img")
    assert img["src"].startswith(f"{DOWNLOAD_DIR_NAME}/remote-")
    downloaded = tmp_path / img["src"]
    assert downloaded.is_file()
    assert downloaded.read_bytes() == b"fake-bytes"


def test_download_remote_images_skips_local_paths(tmp_path: Path):
    soup = BeautifulSoup('<img src="Folder/photo.png"/>', "html.parser")
    with patch("urllib.request.urlopen") as urlopen:
        count = download_remote_images(soup, tmp_path)
    urlopen.assert_not_called()
    assert count == 0
    assert soup.find("img")["src"] == "Folder/photo.png"


def test_download_remote_images_rejects_non_image_response(tmp_path: Path):
    soup = BeautifulSoup(
        '<img src="https://example.com/not-found.jpg"/>', "html.parser"
    )
    with patch(
        "urllib.request.urlopen",
        return_value=_mock_response(b"<html>404</html>", content_type="text/html"),
    ):
        count = download_remote_images(soup, tmp_path)

    assert count == 0
    assert soup.find("img")["src"] == "https://example.com/not-found.jpg"


def test_download_remote_images_handles_network_error(tmp_path: Path):
    import urllib.error

    soup = BeautifulSoup(
        '<img src="https://example.com/unreachable.jpg"/>', "html.parser"
    )
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("boom"),
    ):
        count = download_remote_images(soup, tmp_path)

    assert count == 0
    assert soup.find("img")["src"] == "https://example.com/unreachable.jpg"


def test_download_remote_images_caches_existing_file(tmp_path: Path):
    soup = BeautifulSoup(
        '<img src="https://example.com/photo.jpg"/>', "html.parser"
    )
    with patch("urllib.request.urlopen", return_value=_mock_response(b"x")) as urlopen:
        download_remote_images(soup, tmp_path)

    soup2 = BeautifulSoup(
        '<img src="https://example.com/photo.jpg"/>', "html.parser"
    )
    with patch("urllib.request.urlopen") as urlopen2:
        count = download_remote_images(soup2, tmp_path)

    urlopen2.assert_not_called()
    assert count == 1

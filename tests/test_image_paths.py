from pathlib import Path
from unittest.mock import patch

from notion2tex.image_paths import (
    _convert_to_png,
    fix_includegraphics_paths,
    resolve_image_file,
)


def test_resolve_apostrophe_variant(tmp_path: Path):
    asset = tmp_path / "Economia applicata all\u2019ingegneria"
    asset.mkdir()
    img = asset / "photo.png"
    img.write_bytes(b"x")

    # Pandoc-style ASCII apostrophe in path
    found = resolve_image_file(
        tmp_path, "Economia applicata all'ingegneria/photo.png"
    )
    assert found == img


def test_fix_includegraphics_rewrites_path(tmp_path: Path):
    asset = tmp_path / "Economia applicata all\u2019ingegneria"
    asset.mkdir()
    (asset / "a.png").write_bytes(b"x")

    tex = '\\includegraphics{"Economia applicata all' + "'" + 'ingegneria/a.png"}'
    fixed, n = fix_includegraphics_paths(tex, tmp_path)
    assert n == 1
    assert "\u2019" in fixed
    assert resolve_image_file(tmp_path, fixed.split("{")[1].strip('"}')) is not None


def test_convert_avif_uses_avifdec_on_linux(tmp_path: Path):
    # sips is macOS-only; on Linux (e.g. the Docker image) an AVIF cover
    # image needs a Linux-native decoder or it's silently omitted, even
    # though the exact same export converts fine on a Mac.
    src = tmp_path / "cover.avif"
    src.write_bytes(b"fake-avif")
    dest = tmp_path / "cover.png"

    def fake_which(name):
        return "/usr/bin/avifdec" if name == "avifdec" else None

    def fake_run(cmd, **kwargs):
        assert cmd[0] == "avifdec"
        dest.write_bytes(b"fake-png")

    with patch("notion2tex.image_paths.shutil.which", side_effect=fake_which), patch(
        "notion2tex.image_paths.subprocess.run", side_effect=fake_run
    ):
        assert _convert_to_png(src, dest) is True
    assert dest.is_file()


def test_convert_webp_uses_dwebp_on_linux(tmp_path: Path):
    src = tmp_path / "cover.webp"
    src.write_bytes(b"fake-webp")
    dest = tmp_path / "cover.png"

    def fake_which(name):
        return "/usr/bin/dwebp" if name == "dwebp" else None

    def fake_run(cmd, **kwargs):
        assert cmd[0] == "dwebp"
        dest.write_bytes(b"fake-png")

    with patch("notion2tex.image_paths.shutil.which", side_effect=fake_which), patch(
        "notion2tex.image_paths.subprocess.run", side_effect=fake_run
    ):
        assert _convert_to_png(src, dest) is True


def test_convert_falls_back_to_imagemagick(tmp_path: Path):
    src = tmp_path / "cover.avif"
    src.write_bytes(b"fake-avif")
    dest = tmp_path / "cover.png"

    def fake_which(name):
        return "/usr/bin/magick" if name == "magick" else None

    def fake_run(cmd, **kwargs):
        assert cmd[0] == "magick"
        dest.write_bytes(b"fake-png")

    with patch("notion2tex.image_paths.shutil.which", side_effect=fake_which), patch(
        "notion2tex.image_paths.subprocess.run", side_effect=fake_run
    ):
        assert _convert_to_png(src, dest) is True


def test_convert_returns_false_when_no_tool_available(tmp_path: Path):
    src = tmp_path / "cover.avif"
    src.write_bytes(b"fake-avif")
    dest = tmp_path / "cover.png"

    with patch("notion2tex.image_paths.shutil.which", return_value=None):
        assert _convert_to_png(src, dest) is False
    assert not dest.is_file()

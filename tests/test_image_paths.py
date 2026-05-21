from pathlib import Path

from notion2tex.image_paths import fix_includegraphics_paths, resolve_image_file


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

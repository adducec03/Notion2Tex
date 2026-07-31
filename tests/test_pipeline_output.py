from pathlib import Path

from notion2tex.pipeline import _relocate_output


def test_no_output_leaves_file_in_place(tmp_path: Path):
    src = tmp_path / "Export.pdf"
    src.write_bytes(b"pdf-bytes")

    result = _relocate_output(src, None)

    assert result == src
    assert src.is_file()


def test_relocates_to_custom_path(tmp_path: Path):
    src = tmp_path / "export" / "Export.pdf"
    src.parent.mkdir()
    src.write_bytes(b"pdf-bytes")
    dest = tmp_path / "elsewhere" / "MyNotes.pdf"

    result = _relocate_output(src, dest)

    assert result == dest
    assert dest.is_file()
    assert dest.read_bytes() == b"pdf-bytes"
    assert not src.is_file()


def test_creates_missing_parent_directories(tmp_path: Path):
    src = tmp_path / "Export.pdf"
    src.write_bytes(b"x")
    dest = tmp_path / "a" / "b" / "c" / "Renamed.pdf"

    result = _relocate_output(src, dest)

    assert result == dest
    assert dest.is_file()


def test_expands_user_and_resolves(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    src = tmp_path / "Export.pdf"
    src.write_bytes(b"x")
    dest_str = "~/out.pdf"

    result = _relocate_output(src, dest_str)

    assert result == (tmp_path / "out.pdf").resolve()
    assert result.is_file()

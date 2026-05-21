from pathlib import Path

from notion2tex.cleanup import cleanup_build_artifacts


def test_cleanup_removes_intermediate_files(tmp_path: Path):
    base = "Course"
    kept = {
        tmp_path / "Course.html",
        tmp_path / "Course.tex",
        tmp_path / "Course.pdf",
        tmp_path / "Course.log",
    }
    removed_paths = {
        tmp_path / "Course_clean.html",
        tmp_path / "Course.aux",
        tmp_path / "Course.toc",
        tmp_path / "Course.out",
    }
    for p in kept | removed_paths:
        p.write_text("x", encoding="utf-8")

    removed = cleanup_build_artifacts(tmp_path, base)

    assert set(removed) == removed_paths
    for p in kept:
        assert p.is_file()
    for p in removed_paths:
        assert not p.exists()

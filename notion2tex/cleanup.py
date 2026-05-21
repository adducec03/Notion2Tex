"""Remove intermediate build files after a successful conversion."""

from __future__ import annotations

from pathlib import Path

# Kept: original .html, .tex, .pdf (if built), and pdflatex .log
_INTERMEDIATE_SUFFIXES = (
    "_clean.html",
    ".aux",
    ".toc",
    ".out",
    ".fls",
    ".fdb_latexmk",
    ".synctex.gz",
)


def cleanup_build_artifacts(work_dir: Path, base: str) -> list[Path]:
    """
    Delete preprocessed HTML and LaTeX aux files for *base* in *work_dir*.

    Returns paths that were removed.
    """
    removed: list[Path] = []
    for suffix in _INTERMEDIATE_SUFFIXES:
        path = work_dir / f"{base}{suffix}"
        if path.is_file():
            path.unlink()
            removed.append(path)
    return removed

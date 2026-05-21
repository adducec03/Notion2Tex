"""Resolve Notion image paths for pdflatex (apostrophe variants, AVIF/WebP)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

# Notion folder names often use U+2019; Pandoc may emit ASCII apostrophe.
_APOSTROPHE_CHARS = ("'", "\u2019", "\u0027", "`", "\u00b4")

_PDFLATEX_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".pdf", ".eps"}
_CONVERT_SUFFIXES = {".avif", ".webp"}


def _normalize_apostrophes(text: str) -> str:
    for ch in _APOSTROPHE_CHARS[1:]:
        text = text.replace(ch, _APOSTROPHE_CHARS[0])
    return text


def _apostrophe_alternatives(part: str) -> set[str]:
    alts = {part}
    for ch in _APOSTROPHE_CHARS:
        if ch in part:
            alts.add(part.replace(ch, _APOSTROPHE_CHARS[0]))
            alts.add(part.replace(ch, "\u2019"))
    return alts


def _path_variants(rel: str) -> list[str]:
    """Path strings with alternate apostrophes in every path component."""
    parts = Path(rel).parts
    if not parts:
        return [rel]

    variants: list[list[str]] = [[]]
    for part in parts:
        variants = [
            base + [alt] for base in variants for alt in _apostrophe_alternatives(part)
        ]
    return [str(Path(*v)) for v in variants]


def _match_asset_dir(work_dir: Path, folder_name: str) -> str | None:
    """Find the real asset folder name when apostrophes differ."""
    target = _normalize_apostrophes(folder_name)
    for child in work_dir.iterdir():
        if child.is_dir() and _normalize_apostrophes(child.name) == target:
            return child.name
    return None


def resolve_image_file(work_dir: Path, rel_path: str) -> Path | None:
    """Return an existing file under *work_dir* for a LaTeX graphics path."""
    rel = rel_path.strip().strip('"')
    if not rel:
        return None

    for variant in _path_variants(rel):
        candidate = work_dir / variant
        if candidate.is_file():
            return candidate

    parts = Path(rel).parts
    if len(parts) >= 2:
        real_dir = _match_asset_dir(work_dir, parts[0])
        if real_dir:
            candidate = work_dir / real_dir / Path(*parts[1:])
            if candidate.is_file():
                return candidate

    return None


def _convert_to_png(src: Path, dest: Path) -> bool:
    if dest.is_file():
        return True
    if shutil.which("sips"):
        subprocess.run(
            ["sips", "-s", "format", "png", str(src), "--out", str(dest)],
            capture_output=True,
            check=False,
        )
        return dest.is_file()
    return False


def pdflatex_graphics_path(work_dir: Path, rel_path: str) -> str | None:
    """
    Return a relative path (for \\includegraphics) that pdflatex can load.

    Converts AVIF/WebP to PNG beside the source when needed.
    """
    found = resolve_image_file(work_dir, rel_path)
    if not found:
        return None

    suffix = found.suffix.lower()
    if suffix in _PDFLATEX_IMAGE_SUFFIXES:
        return found.relative_to(work_dir).as_posix()

    if suffix in _CONVERT_SUFFIXES:
        png = found.with_suffix(".png")
        if _convert_to_png(found, png):
            return png.relative_to(work_dir).as_posix()
        return None

    return None


def omit_includegraphics_line() -> str:
    """LaTeX comment placeholder when an image cannot be embedded."""
    return "% [notion2tex] image omitted (missing or unsupported format)\n"


def fix_includegraphics_paths(text: str, work_dir: Path) -> tuple[str, int]:
    """Rewrite \\includegraphics paths to match files on disk."""
    count = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal count
        opts = m.group(1) or ""
        raw = m.group(2).strip().strip('"')
        resolved = pdflatex_graphics_path(work_dir, raw)
        if not resolved:
            suffix = Path(raw.split("/")[-1]).suffix.lower()
            if suffix in _CONVERT_SUFFIXES:
                return omit_includegraphics_line()
            return m.group(0)
        if (
            resolved != raw
            or _normalize_apostrophes(resolved)
            != _normalize_apostrophes(raw)
        ):
            count += 1
        escaped = resolved.replace('"', "'")
        if " " in escaped or "," in escaped:
            return f'\\includegraphics{opts}{{"{escaped}"}}'
        return f"\\includegraphics{opts}{{{escaped}}}"

    text = re.sub(
        r"\\includegraphics(\[[^\]]*\])?\{([^{}]+)\}",
        repl,
        text,
    )
    return text, count

"""Preserve Notion image display widths in LaTeX/PDF output."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup

# Notion HTML export uses ~900px content column (see .page { max-width: 900px })
NOTION_CONTENT_WIDTH_PX = 900.0

# Wider than this (fraction of Notion column) → cap at full \\linewidth
LARGE_IMAGE_FRAC_THRESHOLD = 0.75


def apply_notion_image_sizes(soup) -> int:
    """
    Copy ``style="width: Npx"`` from Notion exports onto ``<img width="N">``.
    Helps Pandoc/LaTeX downstream; also keeps ``data-notion-width-px``.
    """
    count = 0
    for img in soup.find_all("img"):
        if ".svg" in (img.get("src") or "").lower():
            continue
        px = _width_px_from_style(img.get("style", ""))
        if px is None:
            continue
        img["width"] = str(int(round(px)))
        img["data-notion-width-px"] = str(px)
        count += 1
    return count


def _width_px_from_style(style: str) -> float | None:
    match = re.search(r"width:\s*([\d.]+)\s*px", style, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1))


def load_image_width_map(clean_html_path: str | Path) -> dict[str, float]:
    """
    Build a lookup: image path / basename → width as fraction of ``\\linewidth``.
    """
    path = Path(clean_html_path)
    if not path.is_file():
        return {}

    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    widths: dict[str, float] = {}

    for img in soup.find_all("img"):
        src = unquote((img.get("src") or "").strip())
        if not src or ".svg" in src.lower():
            continue

        px = _width_px_from_style(img.get("style", ""))
        if px is None:
            width_attr = img.get("width") or img.get("data-notion-width-px")
            if width_attr:
                try:
                    px = float(width_attr)
                except ValueError:
                    continue
            else:
                continue

        frac = min(px / NOTION_CONTENT_WIDTH_PX, 1.0)
        widths[src] = frac
        widths[Path(src).name] = frac

    return widths


def _width_option_for_fraction(frac: float) -> str:
    """Map Notion width fraction to a graphicx width option."""
    if frac >= LARGE_IMAGE_FRAC_THRESHOLD:
        return r"width=\linewidth"
    return f"width={frac:.4f}\\linewidth"


def _normalize_graphics_options(opts: str, frac: float) -> str:
    """Build safe ``[width=...,keepaspectratio]``; drop Pandoc inch sizes that exceed the page."""
    opts = opts or ""
    opts = re.sub(r",?\s*height=\\textheight", "", opts)

    # Pandoc width=8.24in etc. often exceeds printable area — always use Notion-based size
    width_opt = _width_option_for_fraction(frac)

    parts = [width_opt, "keepaspectratio"]
    inner = opts.strip("[]").strip()
    for piece in inner.split(","):
        piece = piece.strip()
        if not piece or piece.startswith("width=") or piece.startswith("height="):
            continue
        if piece not in parts:
            parts.insert(0, piece)
    return "[" + ",".join(parts) + "]"


def apply_widths_to_includegraphics(
    text: str, widths: dict[str, float]
) -> str:
    """Set ``width=...\\linewidth`` on every ``\\includegraphics`` (replaces Pandoc inch widths)."""

    def repl(match: re.Match[str]) -> str:
        opts = match.group(1) or ""
        raw_path = match.group(2).strip()
        path = raw_path.strip('"')

        frac = widths.get(path) or widths.get(Path(path).name)
        if frac is None:
            frac = 1.0

        new_opts = _normalize_graphics_options(opts, frac)

        if raw_path.startswith('"'):
            body = f'{{"{path}"}}'
        else:
            body = f"{{{path}}}"

        return f"\\includegraphics{new_opts}{body}"

    return re.sub(
        r"\\includegraphics(\[[^\]]*\])?\{([^{}]+)\}",
        repl,
        text,
    )


def unwrap_href_includegraphics(text: str) -> str:
    """Remove hyperlink wrapper around images (Pandoc exports linked PNGs)."""
    graphics = r"(\\includegraphics(?:\[[^\]]*\])?\{[^{}]+\})"
    text = re.sub(rf"\\href\{{[^{{}}]+\}}\{{{graphics}\}}", r"\1", text)
    return text


def center_figure_images(text: str) -> str:
    """Center all figure images (width is capped separately so nothing overflows the page)."""
    text = re.sub(
        r"(\\begin\{figure\}\[H\]\s*)\\raggedright\s*(?:\\noindent\s*)?",
        r"\1\\centering\n",
        text,
    )
    text = re.sub(
        r"(\\begin\{figure\}\[H\]\s*)(?!\\centering\s)((?:\\href\{[^{}]+\}\{)?\\includegraphics)",
        r"\1\\centering\n\2",
        text,
    )
    return text


def neutralize_pandocbounded_scale(text: str) -> str:
    """Stop Pandoc from upscaling every image to full text width/height."""
    return re.sub(
        r"\\newcommand\*\\pandocbounded\[1\]\{%.*?\n\}",
        r"\\newcommand*\\pandocbounded[1]{#1}",
        text,
        count=1,
        flags=re.DOTALL,
    )

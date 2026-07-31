"""Command-line interface for notion2tex."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from notion2tex import __version__
from notion2tex.console import console
from notion2tex.pipeline import convert, missing_tools


def _accent_color_type(value: str) -> str:
    """argparse type=: 6 hex digits, optional leading '#'."""
    digits = value.lstrip("#")
    if len(digits) != 6 or any(c not in "0123456789abcdefABCDEF" for c in digits):
        raise argparse.ArgumentTypeError(
            f"invalid hex color: {value!r} (expected 6 hex digits, e.g. 2E86AB or #2E86AB)"
        )
    return digits.upper()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notion2tex",
        description=(
            "Convert a Notion export to PDF (local pipeline: "
            "clean HTML → Pandoc → LaTeX fixes → pdflatex). "
            "Input: the .zip from Notion, or a single .html inside the export folder."
        ),
    )
    parser.add_argument(
        "input",
        nargs="?",
        metavar="export.zip",
        help="Notion export .zip (recommended) or .html file with its asset folder",
    )
    parser.add_argument(
        "--extract-dir",
        metavar="DIR",
        help="Where to extract the ZIP (default: same name as the .zip, without extension)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that pandoc and pdflatex are available, then exit",
    )
    parser.add_argument(
        "--tex-only",
        action="store_true",
        help="Stop after generating the .tex file (do not run pdflatex)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show pdflatex/pandoc output instead of hiding it",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in terminal output",
    )
    parser.add_argument(
        "--dark",
        action="store_true",
        help="Render the PDF in dark mode (dark gray page, light text and colors)",
    )
    parser.add_argument(
        "--book",
        action="store_true",
        help=(
            "Add book-style structure: designed cover page, table of "
            "contents, a page break before each top-level section, and a "
            "running chapter header. Off by default (continuous document)."
        ),
    )
    parser.add_argument(
        "--lang",
        choices=["en", "it"],
        default=None,
        help=(
            "Document language: loads babel for translated headings "
            "(e.g. table of contents) and correct hyphenation. "
            "Unset by default (plain English kernel defaults)."
        ),
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help=(
            "Skip downloading images Notion only linked to (page covers, "
            "\"image from link\" blocks, bookmark previews) — no network "
            "calls at all, at the cost of omitting those images."
        ),
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help=(
            "Move the finished PDF (or .tex, with --tex-only) to this path "
            "instead of leaving it next to the input. Parent directories "
            "are created if needed."
        ),
    )
    parser.add_argument(
        "--font",
        choices=["serif", "sans"],
        default=None,
        help="Body font family. Unset by default (Latin Modern, today's look).",
    )
    parser.add_argument(
        "--font-size",
        choices=["10", "11", "12"],
        default=None,
        metavar="{10,11,12}",
        help="Base font size in pt. Unset by default (LaTeX's own 10pt).",
    )
    parser.add_argument(
        "--paper",
        choices=["a4", "letter"],
        default=None,
        help=(
            "Page size. Default: a4 (always set explicitly, even if unset "
            "here — otherwise page size silently follows the local TeX "
            "install's ambient default, which varies by machine)."
        ),
    )
    parser.add_argument(
        "--margins",
        choices=["narrow", "normal", "wide"],
        default=None,
        help="Page margins. Default: normal (1in).",
    )
    parser.add_argument(
        "--accent-color",
        type=_accent_color_type,
        default=None,
        metavar="HEX",
        help=(
            "Custom link color, e.g. 2E86AB or #2E86AB. Unset by default "
            "(today's blue, or --dark's own link color)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    console.configure(color=not args.no_color, progress=not args.no_color)

    if args.check:
        missing = missing_tools()
        if missing:
            console.error(f"Missing tools: {', '.join(missing)}")
            print(
                "  Install Pandoc: https://pandoc.org/installing.html",
                file=sys.stderr,
            )
            print(
                "  Install TeX (pdflatex): https://www.tug.org/texlive/",
                file=sys.stderr,
            )
            return 1
        console.success("pandoc and pdflatex are available")
        return 0

    if not args.input:
        parser.error("the following arguments are required: export.zip")

    extract_dir = Path(args.extract_dir) if args.extract_dir else None

    try:
        convert(
            args.input,
            extract_dir=extract_dir,
            tex_only=args.tex_only,
            quiet=not args.verbose,
            dark=args.dark,
            book=args.book,
            lang=args.lang,
            offline=args.offline,
            output=args.output,
            font=args.font,
            font_size=args.font_size,
            paper=args.paper,
            margins=args.margins,
            accent_color=args.accent_color,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        console.error(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

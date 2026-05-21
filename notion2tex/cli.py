"""Command-line interface for notion2tex."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from notion2tex import __version__
from notion2tex.pipeline import convert, missing_tools


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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.check:
        missing = missing_tools()
        if missing:
            print("Missing:", ", ".join(missing), file=sys.stderr)
            print(
                "Install Pandoc: https://pandoc.org/installing.html",
                file=sys.stderr,
            )
            print(
                "Install TeX (pdflatex): https://www.tug.org/texlive/",
                file=sys.stderr,
            )
            return 1
        print("OK: pandoc and pdflatex are available.")
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
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

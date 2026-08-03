"""Command-line interface for notion2tex."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from notion2tex import __version__
from notion2tex import config_file
from notion2tex import interactive
from notion2tex.console import console
from notion2tex.pipeline import convert, missing_tools

# Keys that come from notion2tex.toml and can be overridden by an explicit
# CLI flag. Booleans use "or" (a config default can only be turned further
# on from the CLI, store_true flags have no way to say "explicitly off");
# everything else uses "CLI value if given, else the config's".
_CONFIG_BOOL_KEYS = ("book", "dark", "offline")
_CONFIG_VALUE_KEYS = (
    "lang",
    "output",
    "font",
    "font_size",
    "paper",
    "margins",
    "accent_color",
)


def _accent_color_type(value: str) -> str:
    """argparse type=: 6 hex digits, optional leading '#'."""
    try:
        return config_file.validate_accent_color(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _merge_with_config(args: dict, config: dict) -> dict:
    """
    Layer a notion2tex.toml config dict under explicit CLI arg values.
    *args* and the return value use the same key names as _CONFIG_BOOL_KEYS
    + _CONFIG_VALUE_KEYS (a plain dict, not argparse.Namespace, so this is
    testable without building a real parser).
    """
    merged = dict(args)
    for key in _CONFIG_BOOL_KEYS:
        merged[key] = bool(args.get(key)) or bool(config.get(key, False))
    for key in _CONFIG_VALUE_KEYS:
        merged[key] = args.get(key) if args.get(key) is not None else config.get(key)
    return merged


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
        "--config",
        action="store_true",
        help=(
            "Open an interactive menu to create/use/edit/delete named "
            "profiles of export defaults (book, lang, dark, offline, "
            "output, font, paper, margins, accent color), stored in a "
            "global config directory (~/.config/notion2tex, or "
            "%%APPDATA%%\\notion2tex on Windows), then exit. The active "
            "profile applies automatically on later runs; explicit CLI "
            "flags still override it. See --profile to use one without "
            "changing which is active."
        ),
    )
    parser.add_argument(
        "--profile",
        metavar="NAME",
        default=None,
        help=(
            "Use this saved profile for this run only, instead of "
            "whichever one is currently active (see --config)."
        ),
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
        choices=["8", "9", "10", "11", "12", "14", "17", "20"],
        default=None,
        metavar="{8,9,10,11,12,14,17,20}",
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

    if args.config:
        try:
            return interactive.run_config_command()
        except EOFError:
            console.error(
                "--config needs a real interactive terminal. "
                "Running in Docker? Add -it to `docker run` (docker-compose "
                "and the notion2tex-docker.sh/.ps1 wrapper scripts already do)."
            )
            return 1

    if not args.input:
        parser.error("the following arguments are required: export.zip")

    extract_dir = Path(args.extract_dir) if args.extract_dir else None

    opts = {key: getattr(args, key) for key in _CONFIG_BOOL_KEYS + _CONFIG_VALUE_KEYS}
    profile_name = args.profile or config_file.get_active_profile()
    if profile_name is not None:
        resolved_path = config_file.profile_path(profile_name)
        if not resolved_path.is_file():
            parser.error(f'no such profile: "{profile_name}" ({resolved_path})')
        console.detail(f'Using profile "{profile_name}" ({resolved_path})')
        opts = _merge_with_config(opts, config_file.load_config(resolved_path))

    try:
        convert(
            args.input,
            extract_dir=extract_dir,
            tex_only=args.tex_only,
            quiet=not args.verbose,
            dark=opts["dark"],
            book=opts["book"],
            lang=opts["lang"],
            offline=opts["offline"],
            output=opts["output"],
            font=opts["font"],
            font_size=opts["font_size"],
            paper=opts["paper"],
            margins=opts["margins"],
            accent_color=opts["accent_color"],
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        console.error(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

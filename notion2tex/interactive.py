"""Interactive `--config` menu: choose export defaults with arrow keys
instead of remembering CLI flags, and save them to notion2tex.toml.
"""

from __future__ import annotations

from pathlib import Path

from notion2tex.config_file import CONFIG_FILENAME, validate_accent_color, write_config
from notion2tex.console import console

_UNSET = "Unset (default)"


def _select(question: str, choices: list[str], default: str) -> str | None:
    import questionary

    return questionary.select(question, choices=choices, default=default).ask()


def _confirm(question: str) -> bool | None:
    import questionary

    return questionary.confirm(question, default=False).ask()


def _text(question: str) -> str | None:
    import questionary

    return questionary.text(question).ask()


def _accent_color_prompt() -> str | None:
    import questionary

    def validator(value: str) -> bool | str:
        if not value.strip():
            return True
        try:
            validate_accent_color(value.strip())
        except ValueError as exc:
            return str(exc)
        return True

    return questionary.text(
        "Accent color (6 hex digits, e.g. 2E86AB — leave empty to skip)?",
        validate=validator,
    ).ask()


def run_config_menu() -> dict | None:
    """
    Walk through every export option interactively. Returns the chosen
    config dict, or None if the user cancelled (Ctrl-C) at any point —
    callers should not write anything in that case.
    """
    console.detail("notion2tex --config — choose your export defaults (arrows + Enter, Ctrl-C to cancel)")
    config: dict = {}

    book = _confirm("Book mode (cover page, table of contents, chapter breaks)?")
    if book is None:
        return None
    if book:
        config["book"] = True

    lang = _select(
        "Language (translated headings + hyphenation)?",
        [_UNSET, "English (en)", "Italiano (it)"],
        _UNSET,
    )
    if lang is None:
        return None
    if lang == "English (en)":
        config["lang"] = "en"
    elif lang == "Italiano (it)":
        config["lang"] = "it"

    dark = _confirm("Dark mode?")
    if dark is None:
        return None
    if dark:
        config["dark"] = True

    offline = _confirm("Offline mode (no network calls, skips linked images)?")
    if offline is None:
        return None
    if offline:
        config["offline"] = True

    output = _text("Custom output path for the PDF (leave empty for the default location)?")
    if output is None:
        return None
    if output.strip():
        config["output"] = output.strip()

    font = _select(
        "Font family?",
        [_UNSET, "Serif (Times-like)", "Sans (Helvetica-like)"],
        _UNSET,
    )
    if font is None:
        return None
    if font == "Serif (Times-like)":
        config["font"] = "serif"
    elif font == "Sans (Helvetica-like)":
        config["font"] = "sans"

    font_size = _select("Font size?", [_UNSET, "11pt", "12pt"], _UNSET)
    if font_size is None:
        return None
    if font_size == "11pt":
        config["font_size"] = "11"
    elif font_size == "12pt":
        config["font_size"] = "12"

    paper = _select("Paper size?", ["A4 (default)", "Letter"], "A4 (default)")
    if paper is None:
        return None
    if paper == "Letter":
        config["paper"] = "letter"

    margins = _select("Margins?", ["Narrow", "Normal (default)", "Wide"], "Normal (default)")
    if margins is None:
        return None
    if margins == "Narrow":
        config["margins"] = "narrow"
    elif margins == "Wide":
        config["margins"] = "wide"

    accent_color = _accent_color_prompt()
    if accent_color is None:
        return None
    if accent_color.strip():
        config["accent_color"] = validate_accent_color(accent_color.strip())

    return config


def run_config_and_save(directory: Path) -> int:
    """Entry point for `notion2tex --config`. Returns a process exit code."""
    config = run_config_menu()
    if config is None:
        console.warn("Cancelled — nothing saved.")
        return 1

    dest = directory / CONFIG_FILENAME
    if not config:
        console.detail("No options selected — every setting stays at its built-in default.")

    if dest.is_file():
        overwrite = _confirm(f"{dest} already exists — overwrite it?")
        if not overwrite:
            console.warn("Cancelled — existing file left untouched.")
            return 1

    write_config(dest, config)
    console.success(f"Saved defaults to {dest}")
    console.detail("They'll be picked up automatically next time you run notion2tex here.")
    return 0

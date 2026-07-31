"""Interactive `--config` menu: create/use/edit/delete named profiles
with arrow keys instead of remembering CLI flags every time.
"""

from __future__ import annotations

from notion2tex import config_file
from notion2tex.console import console

_UNSET = "Unset (default)"

# Each option's (label, stored-value) pairs. `None` stored value means
# "leave the key out of the profile entirely" (today's built-in default
# applies). Shared between creating a profile from scratch (existing={})
# and editing one (existing=the loaded profile) -- the label pre-selected
# for a `select` prompt is whichever one's stored value matches what's
# already in *existing*.
_LANG_CHOICES = [(_UNSET, None), ("English (en)", "en"), ("Italiano (it)", "it")]
_FONT_CHOICES = [(_UNSET, None), ("Serif (Times-like)", "serif"), ("Sans (Helvetica-like)", "sans")]
_FONT_SIZE_CHOICES = [(_UNSET, None), ("11pt", "11"), ("12pt", "12")]
_PAPER_CHOICES = [("A4 (default)", None), ("Letter", "letter")]
_MARGINS_CHOICES = [("Narrow", "narrow"), ("Normal (default)", None), ("Wide", "wide")]


def _label_for_value(choices: list[tuple[str, object]], value: object) -> str:
    for label, v in choices:
        if v == value:
            return label
    return choices[0][0]


def _value_for_label(choices: list[tuple[str, object]], label: str) -> object:
    for l, v in choices:
        if l == label:
            return v
    return None


def _select(question: str, choices: list[str], default: str) -> str | None:
    import questionary

    return questionary.select(question, choices=choices, default=default).ask()


def _confirm(question: str, default: bool = False) -> bool | None:
    import questionary

    return questionary.confirm(question, default=default).ask()


def _text(question: str, default: str = "") -> str | None:
    import questionary

    return questionary.text(question, default=default).ask()


def _accent_color_prompt(default: str = "") -> str | None:
    import questionary

    def validator(value: str) -> bool | str:
        if not value.strip():
            return True
        try:
            config_file.validate_accent_color(value.strip())
        except ValueError as exc:
            return str(exc)
        return True

    return questionary.text(
        "Accent color (6 hex digits, e.g. 2E86AB — leave empty to skip)?",
        default=default,
        validate=validator,
    ).ask()


def _prompt_all_options(existing: dict) -> dict | None:
    """
    Walk through every export option interactively, pre-filled from
    *existing* (an empty dict for a brand-new profile, a loaded one when
    editing). Returns the chosen config dict, or None if the user
    cancelled (Ctrl-C) at any point -- callers should not save anything
    in that case.
    """
    config: dict = {}

    book = _confirm(
        "Book mode (cover page, table of contents, chapter breaks)?",
        default=bool(existing.get("book", False)),
    )
    if book is None:
        return None
    if book:
        config["book"] = True

    lang = _select(
        "Language (translated headings + hyphenation)?",
        [label for label, _ in _LANG_CHOICES],
        _label_for_value(_LANG_CHOICES, existing.get("lang")),
    )
    if lang is None:
        return None
    value = _value_for_label(_LANG_CHOICES, lang)
    if value is not None:
        config["lang"] = value

    dark = _confirm("Dark mode?", default=bool(existing.get("dark", False)))
    if dark is None:
        return None
    if dark:
        config["dark"] = True

    offline = _confirm(
        "Offline mode (no network calls, skips linked images)?",
        default=bool(existing.get("offline", False)),
    )
    if offline is None:
        return None
    if offline:
        config["offline"] = True

    output = _text(
        "Custom output path for the PDF (leave empty for the default location)?",
        default=existing.get("output") or "",
    )
    if output is None:
        return None
    if output.strip():
        config["output"] = output.strip()

    font = _select(
        "Font family?",
        [label for label, _ in _FONT_CHOICES],
        _label_for_value(_FONT_CHOICES, existing.get("font")),
    )
    if font is None:
        return None
    value = _value_for_label(_FONT_CHOICES, font)
    if value is not None:
        config["font"] = value

    font_size = _select(
        "Font size?",
        [label for label, _ in _FONT_SIZE_CHOICES],
        _label_for_value(_FONT_SIZE_CHOICES, existing.get("font_size")),
    )
    if font_size is None:
        return None
    value = _value_for_label(_FONT_SIZE_CHOICES, font_size)
    if value is not None:
        config["font_size"] = value

    paper = _select(
        "Paper size?",
        [label for label, _ in _PAPER_CHOICES],
        _label_for_value(_PAPER_CHOICES, existing.get("paper")),
    )
    if paper is None:
        return None
    value = _value_for_label(_PAPER_CHOICES, paper)
    if value is not None:
        config["paper"] = value

    margins = _select(
        "Margins?",
        [label for label, _ in _MARGINS_CHOICES],
        _label_for_value(_MARGINS_CHOICES, existing.get("margins")),
    )
    if margins is None:
        return None
    value = _value_for_label(_MARGINS_CHOICES, margins)
    if value is not None:
        config["margins"] = value

    accent_color = _accent_color_prompt(default=existing.get("accent_color") or "")
    if accent_color is None:
        return None
    if accent_color.strip():
        config["accent_color"] = config_file.validate_accent_color(accent_color.strip())

    return config


def _format_active_line() -> str:
    active = config_file.get_active_profile()
    if active is None:
        return "Active profile: none (built-in defaults)"
    return f"Active profile: {active} ({config_file.profile_path(active)})"


def _action_create() -> None:
    name = _text("Name for the new profile (letters, digits, - or _)?")
    if name is None:
        return
    try:
        name = config_file.validate_profile_name(name)
    except ValueError as exc:
        console.error(str(exc))
        return

    dest = config_file.profile_path(name)
    if dest.is_file():
        overwrite = _confirm(f'A profile named "{name}" already exists — overwrite it?')
        if not overwrite:
            console.warn("Cancelled.")
            return

    config = _prompt_all_options({})
    if config is None:
        console.warn("Cancelled — nothing saved.")
        return

    config_file.write_config(dest, config)
    console.success(f'Saved profile "{name}" to {dest}')

    make_active = _confirm(f'Set "{name}" as the active profile now?', default=True)
    if make_active:
        config_file.set_active_profile(name)
        console.detail(f'"{name}" is now active.')


def _action_edit() -> None:
    names = config_file.list_profiles()
    name = _select("Which profile do you want to edit?", names, names[0])
    if name is None:
        return

    existing = config_file.load_config(config_file.profile_path(name))
    config = _prompt_all_options(existing)
    if config is None:
        console.warn("Cancelled — no changes saved.")
        return

    config_file.write_config(config_file.profile_path(name), config)
    console.success(f'Updated profile "{name}"')


def _action_use() -> None:
    names = config_file.list_profiles()
    active = config_file.get_active_profile()
    labels = [f"{n} (active)" if n == active else n for n in names]

    chosen = _select("Which profile should be active?", labels, labels[0])
    if chosen is None:
        return

    name = chosen.removesuffix(" (active)")
    config_file.set_active_profile(name)
    console.success(f'"{name}" is now the active profile.')


def _action_delete() -> None:
    names = config_file.list_profiles()
    name = _select("Which profile do you want to delete?", names, names[0])
    if name is None:
        return

    confirmed = _confirm(f'Delete profile "{name}"? This cannot be undone.')
    if not confirmed:
        console.warn("Cancelled.")
        return

    config_file.delete_profile(name)
    console.success(f'Deleted profile "{name}"')


def _action_clear_active() -> None:
    active = config_file.get_active_profile()
    config_file.set_active_profile(None)
    console.success(f'Cleared active profile (was "{active}"). Using built-in defaults now.')


_ACTIONS = {
    "Use an existing profile": _action_use,
    "Create a new profile": _action_create,
    "Edit an existing profile": _action_edit,
    "Delete a profile": _action_delete,
    "Clear active profile (use built-in defaults)": _action_clear_active,
}


def run_config_command() -> int:
    """Entry point for `notion2tex --config`. Returns a process exit code."""
    while True:
        console.detail(_format_active_line())

        names = config_file.list_profiles()
        active = config_file.get_active_profile()

        choices = []
        if names:
            choices.append("Use an existing profile")
        choices.append("Create a new profile")
        if names:
            choices.append("Edit an existing profile")
            choices.append("Delete a profile")
        if active is not None:
            choices.append("Clear active profile (use built-in defaults)")
        choices.append("Cancel")

        action = _select("What do you want to do?", choices, choices[0])
        if action is None or action == "Cancel":
            return 0

        _ACTIONS[action]()
        print()

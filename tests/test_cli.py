import pytest

from notion2tex.cli import _accent_color_type, _build_parser, _merge_with_config


def test_book_flag_defaults_to_false():
    args = _build_parser().parse_args(["export.zip"])
    assert args.book is False


def test_book_flag_enabled():
    args = _build_parser().parse_args(["export.zip", "--book"])
    assert args.book is True


def test_dark_and_book_are_independent():
    args = _build_parser().parse_args(["export.zip", "--dark"])
    assert args.dark is True
    assert args.book is False


def test_lang_flag_defaults_to_none():
    args = _build_parser().parse_args(["export.zip"])
    assert args.lang is None


def test_lang_flag_accepts_supported_codes():
    args = _build_parser().parse_args(["export.zip", "--lang", "it"])
    assert args.lang == "it"


def test_lang_flag_rejects_unsupported_code():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["export.zip", "--lang", "fr"])


def test_offline_flag_defaults_to_false():
    args = _build_parser().parse_args(["export.zip"])
    assert args.offline is False


def test_offline_flag_enabled():
    args = _build_parser().parse_args(["export.zip", "--offline"])
    assert args.offline is True


def test_output_flag_defaults_to_none():
    args = _build_parser().parse_args(["export.zip"])
    assert args.output is None


def test_output_flag_accepts_path():
    args = _build_parser().parse_args(["export.zip", "--output", "/tmp/MyNotes.pdf"])
    assert args.output == "/tmp/MyNotes.pdf"


def test_appearance_flags_default_to_none():
    args = _build_parser().parse_args(["export.zip"])
    assert args.font is None
    assert args.font_size is None
    assert args.paper is None
    assert args.margins is None
    assert args.accent_color is None


def test_font_flag_accepts_supported_values():
    args = _build_parser().parse_args(["export.zip", "--font", "serif"])
    assert args.font == "serif"


def test_font_flag_rejects_unsupported_value():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["export.zip", "--font", "comic-sans"])


def test_font_size_flag_accepts_supported_values():
    args = _build_parser().parse_args(["export.zip", "--font-size", "12"])
    assert args.font_size == "12"


def test_paper_and_margins_flags():
    args = _build_parser().parse_args(
        ["export.zip", "--paper", "letter", "--margins", "wide"]
    )
    assert args.paper == "letter"
    assert args.margins == "wide"


def test_accent_color_flag_parses_bare_hex():
    args = _build_parser().parse_args(["export.zip", "--accent-color", "2e86ab"])
    assert args.accent_color == "2E86AB"


def test_accent_color_flag_parses_hash_prefixed_hex():
    args = _build_parser().parse_args(["export.zip", "--accent-color", "#2E86AB"])
    assert args.accent_color == "2E86AB"


def test_accent_color_flag_rejects_invalid_value():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["export.zip", "--accent-color", "not-a-color"])


def test_accent_color_type_accepts_bare_and_hash_prefixed():
    assert _accent_color_type("2e86ab") == "2E86AB"
    assert _accent_color_type("#2e86ab") == "2E86AB"


def test_accent_color_type_rejects_invalid():
    import argparse

    for bad in ("zzzzzz", "2E86A", "2E86ABC", ""):
        with pytest.raises(argparse.ArgumentTypeError):
            _accent_color_type(bad)


def test_config_flag_defaults_to_false():
    args = _build_parser().parse_args(["export.zip"])
    assert args.config is False


def test_config_flag_enabled():
    args = _build_parser().parse_args(["--config"])
    assert args.config is True


def test_config_flag_works_without_input():
    # --config is a standalone action, like --check: no export.zip required.
    args = _build_parser().parse_args(["--config"])
    assert args.input is None


_EMPTY_ARGS = {
    "book": False,
    "dark": False,
    "offline": False,
    "lang": None,
    "output": None,
    "font": None,
    "font_size": None,
    "paper": None,
    "margins": None,
    "accent_color": None,
}


def test_merge_config_fills_in_when_cli_absent():
    merged = _merge_with_config(_EMPTY_ARGS, {"book": True, "lang": "it"})
    assert merged["book"] is True
    assert merged["lang"] == "it"


def test_merge_config_cli_flag_overrides_value_option():
    args = {**_EMPTY_ARGS, "lang": "en"}
    merged = _merge_with_config(args, {"lang": "it"})
    assert merged["lang"] == "en"


def test_merge_config_boolean_or_semantics():
    # config says dark=True, CLI didn't pass --dark -> still dark
    merged = _merge_with_config(_EMPTY_ARGS, {"dark": True})
    assert merged["dark"] is True

    # CLI passed --dark, config doesn't mention it -> still dark
    args = {**_EMPTY_ARGS, "dark": True}
    merged = _merge_with_config(args, {})
    assert merged["dark"] is True


def test_merge_config_missing_keys_default_to_none_or_false():
    merged = _merge_with_config(_EMPTY_ARGS, {})
    assert merged["book"] is False
    assert merged["lang"] is None


def test_merge_config_does_not_mutate_input_dicts():
    args = dict(_EMPTY_ARGS)
    config = {"book": True}
    _merge_with_config(args, config)
    assert args == _EMPTY_ARGS
    assert config == {"book": True}

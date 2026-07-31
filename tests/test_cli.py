import pytest

from notion2tex.cli import _build_parser


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

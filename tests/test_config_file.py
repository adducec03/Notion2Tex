from pathlib import Path

import pytest

from notion2tex.config_file import (
    CONFIG_FILENAME,
    find_config,
    load_config,
    validate_accent_color,
    write_config,
)


def test_find_config_present(tmp_path: Path):
    (tmp_path / CONFIG_FILENAME).write_text("book = true\n", encoding="utf-8")
    assert find_config(tmp_path) == tmp_path / CONFIG_FILENAME


def test_find_config_absent(tmp_path: Path):
    assert find_config(tmp_path) is None


def test_write_then_load_round_trip(tmp_path: Path):
    path = tmp_path / CONFIG_FILENAME
    config = {
        "book": True,
        "dark": False,
        "lang": "it",
        "paper": "a4",
        "accent_color": "2E86AB",
    }
    write_config(path, config)
    loaded = load_config(path)

    assert loaded["book"] is True
    assert loaded["lang"] == "it"
    assert loaded["paper"] == "a4"
    assert loaded["accent_color"] == "2E86AB"
    # dark=False was in the input dict but should still round-trip if written
    assert loaded.get("dark") is False


def test_write_config_omits_keys_not_provided(tmp_path: Path):
    path = tmp_path / CONFIG_FILENAME
    write_config(path, {"book": True})
    loaded = load_config(path)
    assert loaded == {"book": True}


def test_write_config_omits_none_values(tmp_path: Path):
    path = tmp_path / CONFIG_FILENAME
    write_config(path, {"book": True, "lang": None})
    loaded = load_config(path)
    assert "lang" not in loaded


def test_validate_accent_color_accepts_bare_and_hash_prefixed():
    assert validate_accent_color("2e86ab") == "2E86AB"
    assert validate_accent_color("#2e86ab") == "2E86AB"


def test_validate_accent_color_rejects_invalid():
    for bad in ("zzzzzz", "2E86A", "2E86ABC", ""):
        with pytest.raises(ValueError):
            validate_accent_color(bad)

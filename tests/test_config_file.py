from pathlib import Path

import pytest

from notion2tex import config_file


@pytest.fixture(autouse=True)
def isolated_config_dir(tmp_path: Path, monkeypatch):
    """Every test gets its own config dir -- never touch the real ~/.config."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    yield tmp_path / "notion2tex"


def test_config_dir_is_created(isolated_config_dir: Path):
    d = config_file.config_dir()
    assert d == isolated_config_dir
    assert d.is_dir()


def test_config_dir_respects_xdg_config_home(tmp_path: Path, monkeypatch):
    custom = tmp_path / "somewhere-else"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(custom))
    assert config_file.config_dir() == custom / "notion2tex"


def test_validate_profile_name_accepts_safe_names():
    assert config_file.validate_profile_name("book") == "book"
    assert config_file.validate_profile_name("quick-notes_v2") == "quick-notes_v2"


def test_validate_profile_name_rejects_unsafe_names():
    for bad in ("", "  ", "a/b", "../escape", "a b", "a.b"):
        with pytest.raises(ValueError):
            config_file.validate_profile_name(bad)


def test_profile_path_uses_config_dir(isolated_config_dir: Path):
    assert config_file.profile_path("book") == isolated_config_dir / "book.toml"


def test_list_profiles_empty_when_none():
    assert config_file.list_profiles() == []


def test_list_profiles_returns_sorted_names():
    config_file.write_config(config_file.profile_path("zeta"), {"book": True})
    config_file.write_config(config_file.profile_path("alpha"), {"dark": True})
    assert config_file.list_profiles() == ["alpha", "zeta"]


def test_active_profile_none_by_default():
    assert config_file.get_active_profile() is None


def test_set_and_get_active_profile():
    config_file.write_config(config_file.profile_path("book"), {"book": True})
    config_file.set_active_profile("book")
    assert config_file.get_active_profile() == "book"


def test_active_profile_none_when_marker_points_at_deleted_profile():
    config_file.write_config(config_file.profile_path("book"), {"book": True})
    config_file.set_active_profile("book")
    config_file.profile_path("book").unlink()
    assert config_file.get_active_profile() is None


def test_clear_active_profile():
    config_file.write_config(config_file.profile_path("book"), {"book": True})
    config_file.set_active_profile("book")
    config_file.set_active_profile(None)
    assert config_file.get_active_profile() is None


def test_delete_profile_removes_file():
    path = config_file.profile_path("book")
    config_file.write_config(path, {"book": True})
    config_file.delete_profile("book")
    assert not path.is_file()


def test_delete_profile_clears_active_marker_if_it_was_active():
    config_file.write_config(config_file.profile_path("book"), {"book": True})
    config_file.set_active_profile("book")
    config_file.delete_profile("book")
    assert config_file.get_active_profile() is None


def test_delete_profile_leaves_other_active_profile_alone():
    config_file.write_config(config_file.profile_path("book"), {"book": True})
    config_file.write_config(config_file.profile_path("dark"), {"dark": True})
    config_file.set_active_profile("dark")
    config_file.delete_profile("book")
    assert config_file.get_active_profile() == "dark"


def test_write_then_load_round_trip():
    path = config_file.profile_path("book")
    config = {
        "book": True,
        "dark": False,
        "lang": "it",
        "paper": "a4",
        "accent_color": "2E86AB",
    }
    config_file.write_config(path, config)
    loaded = config_file.load_config(path)

    assert loaded["book"] is True
    assert loaded["lang"] == "it"
    assert loaded["paper"] == "a4"
    assert loaded["accent_color"] == "2E86AB"
    assert loaded.get("dark") is False


def test_write_config_omits_keys_not_provided():
    path = config_file.profile_path("book")
    config_file.write_config(path, {"book": True})
    assert config_file.load_config(path) == {"book": True}


def test_write_config_omits_none_values():
    path = config_file.profile_path("book")
    config_file.write_config(path, {"book": True, "lang": None})
    loaded = config_file.load_config(path)
    assert "lang" not in loaded


def test_validate_accent_color_accepts_bare_and_hash_prefixed():
    assert config_file.validate_accent_color("2e86ab") == "2E86AB"
    assert config_file.validate_accent_color("#2e86ab") == "2E86AB"


def test_validate_accent_color_rejects_invalid():
    for bad in ("zzzzzz", "2E86A", "2E86ABC", ""):
        with pytest.raises(ValueError):
            config_file.validate_accent_color(bad)

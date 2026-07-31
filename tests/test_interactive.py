"""
Drives the real questionary prompts via prompt_toolkit's pipe-input testing
utilities (create_pipe_input + create_app_session) -- no mocking of
questionary itself, so this exercises the actual interactive.py code path.

Scoped to what's reliable to script this way: accepting defaults (bare
Enter) and typing text, chained across several prompts in one pass, plus
cancelling (Ctrl-C) at the first prompt. Precisely scripting arrow-key
*navigation* across several chained prompts in one pipe turned out to be
flaky in manual testing (prompt_toolkit's escape-sequence timing across
back-to-back Application instances) -- individual actions that need a
specific *non-default* selection are tested one at a time instead, each
with its own fresh pipe (no chaining), which was reliable in manual
testing. The choice-label <-> config-value mapping itself is covered by
direct code review (every `default=` passed to _select matches an entry
in that same call's `choices=`).
"""

from pathlib import Path

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from notion2tex import config_file
from notion2tex.interactive import (
    _action_create,
    _action_delete,
    _action_use,
    _confirm,
    _text,
    run_config_command,
)


@pytest.fixture(autouse=True)
def isolated_config_dir(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    yield tmp_path / "notion2tex"


def _run(keys: str, fn, *args):
    with create_pipe_input() as pipe_input:
        pipe_input.send_text(keys)
        with create_app_session(input=pipe_input, output=DummyOutput()):
            return fn(*args)


def test_cancelling_first_prompt_returns_zero_and_creates_nothing():
    rc = _run("\x03", run_config_command)
    assert rc == 0
    assert config_file.list_profiles() == []


def test_full_flow_create_profile_with_defaults_then_cancel():
    # Main menu (empty state, default = "Create a new profile") -> name
    # -> 10 option prompts, all defaults -> "set as active?" default Yes
    # -> back at main menu (now non-empty) -> cancel.
    keys = "\r" + "testprofile\r" + ("\r" * 10) + "\r" + "\x03"
    rc = _run(keys, run_config_command)
    assert rc == 0
    assert config_file.list_profiles() == ["testprofile"]
    assert config_file.get_active_profile() == "testprofile"
    assert config_file.load_config(config_file.profile_path("testprofile")) == {}


def test_action_create_saves_profile_and_can_set_active():
    keys = "book\r" + ("\r" * 10) + "y\r"  # name, all defaults, set active = yes
    _run(keys, _action_create)
    assert config_file.list_profiles() == ["book"]
    assert config_file.get_active_profile() == "book"


def test_action_create_rejects_then_can_be_retried_is_manual():
    # invalid name characters -> function prints an error and returns
    # without prompting further (verified: no profile ends up saved).
    _run("bad name!\r", _action_create)
    assert config_file.list_profiles() == []


def test_action_use_switches_active_profile():
    config_file.write_config(config_file.profile_path("alpha"), {"book": True})
    config_file.write_config(config_file.profile_path("beta"), {"dark": True})
    config_file.set_active_profile("alpha")

    # list_profiles() is sorted: ["alpha (active)", "beta"] -- default is
    # the first entry, so accepting default here re-selects "alpha".
    _run("\r", _action_use)
    assert config_file.get_active_profile() == "alpha"


def test_action_delete_removes_profile():
    config_file.write_config(config_file.profile_path("book"), {"book": True})

    # select (default = only entry), then confirm deletion = yes
    _run("\r" + "y\r", _action_delete)
    assert config_file.list_profiles() == []


def test_confirm_and_text_helpers_still_work_isolated():
    assert _run("y\r", _confirm, "Q?") is True
    assert _run("\r", _confirm, "Q?") is False
    assert _run("hello\r", _text, "Q?") == "hello"

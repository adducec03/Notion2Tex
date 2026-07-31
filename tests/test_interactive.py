"""
Drives the real questionary prompts via prompt_toolkit's pipe-input testing
utilities (create_pipe_input + create_app_session) -- no mocking of
questionary itself, so this exercises the actual interactive.py code path.

Scoped to what's reliable to script this way: accepting every default in
one pass, and cancelling (Ctrl-C) at the very first prompt. Precisely
scripting arrow-key navigation across several *chained* prompts in one
pipe turned out to be flaky in manual testing (prompt_toolkit's escape-
sequence timing across back-to-back Application instances) -- the
choice-label <-> config-value mapping for each individual prompt is
covered instead by direct code review (every `default=` passed to
_select matches an entry in that same call's `choices=`, and every
comparison string matches a `choices=` entry byte-for-byte).
"""

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from notion2tex.interactive import _confirm, _text, run_config_menu


def _run(keys: str, fn, *args):
    with create_pipe_input() as pipe_input:
        pipe_input.send_text(keys)
        with create_app_session(input=pipe_input, output=DummyOutput()):
            return fn(*args)


def test_accepting_every_default_produces_empty_config():
    # 10 prompts total (book, lang, dark, offline, output, font, font_size,
    # paper, margins, accent_color); a bare Enter accepts each default.
    result = _run("\r" * 10, run_config_menu)
    assert result == {}


def test_cancelling_first_prompt_returns_none():
    result = _run("\x03", run_config_menu)
    assert result is None


def test_confirm_accepts_yes():
    assert _run("y\r", _confirm, "Q?") is True


def test_confirm_accepts_default_on_bare_enter():
    assert _run("\r", _confirm, "Q?") is False


def test_text_returns_typed_value():
    assert _run("hello\r", _text, "Q?") == "hello"


def test_text_returns_empty_on_bare_enter():
    assert _run("\r", _text, "Q?") == ""

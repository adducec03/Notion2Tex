"""Tests for separating LaTeX commands glued to ASCII letters."""

from notion2tex.fix_latex import _fix_pandoc_char_escapes
from notion2tex.katex_latex import normalize_katex
from notion2tex.unicode_map import separate_glued_command_letters


def test_microseconds_unicode_literal():
    assert normalize_katex("125 μs") == r"125 \mu s"


def test_pi_glued_to_variable():
    assert normalize_katex("2πf") == r"2\pi f"
    assert normalize_katex(r"cos(2πf_ct)") == r"cos(2\pi f_ct)"


def test_pandoc_char_escape_glued():
    assert _fix_pandoc_char_escapes(r'125 \char"00B5s') == r"125 \ensuremath{\mu }s"
    assert _fix_pandoc_char_escapes(r'\char"03BCs') == r"\ensuremath{\mu }s"


def test_does_not_break_includegraphics():
    tex = r"\includegraphics{x.png}"
    assert separate_glued_command_letters(tex) == tex


def test_idempotent():
    once = separate_glued_command_letters(r"\mus e")
    twice = separate_glued_command_letters(once)
    assert once == twice == r"\mu s e"

"""Tests for Unicode → LaTeX mappings."""

from notion2tex.unicode_map import UNICODE_MATH, latex_for_codepoint

# Unassigned code point between Greek Pi and Rho (skip in range scans)
_UNASSIGNED_GREEK = {"03A2"}


def test_all_lowercase_greek_mapped():
    for cp in range(0x03B1, 0x03CA):
        key = format(cp, "04X")
        assert key in UNICODE_MATH, key


def test_all_uppercase_greek_mapped():
    for cp in range(0x0391, 0x03AA):
        key = format(cp, "04X")
        if key in _UNASSIGNED_GREEK:
            continue
        assert key in UNICODE_MATH, key


def test_common_operators():
    assert latex_for_codepoint("2208") == r"\in"
    assert latex_for_codepoint("2200") == r"\forall"
    assert latex_for_codepoint("251C") == r"\vdash"

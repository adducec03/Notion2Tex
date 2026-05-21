from notion2tex.fix_latex import _ensure_strikeout_support

PANDOC_BLOCK = r"""
\ifLuaTeX
  \usepackage{luacolor}
  \usepackage[soul]{lua-ul}
\else
  \usepackage{soul}
\fi
"""


def test_strikeout_falls_back_when_soul_missing():
    fixed = _ensure_strikeout_support(PANDOC_BLOCK)
    assert r"\usepackage{soul}" not in fixed or "IfFileExists{soul.sty}" in fixed
    assert "IfFileExists{soul.sty}" in fixed
    assert "ulem" in fixed

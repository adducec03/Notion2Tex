from notion2tex.console import Console, _ProgressBar


def test_console_no_color_plain_output(capsys):
    c = Console(color=False, progress=False)
    c.step(1, 4, "Clean HTML")
    c.detail("439 toggles converted")
    c.success("Done: out.pdf")
    out = capsys.readouterr().out
    assert "[1/4] Clean HTML" in out
    assert "439 toggles converted" in out
    assert "Done: out.pdf" in out
    assert "\033[" not in out


def test_progress_bar_disabled_falls_back_to_detail(capsys):
    c = Console(color=False, progress=False)
    bar = c.progress(3, "Test")
    bar.advance()
    bar.advance()
    bar.finish("Test — done")
    out = capsys.readouterr().out
    assert "done" in out.lower()


def test_progress_bar_render_format():
    c = Console(color=False, progress=True)
    bar = _ProgressBar(c, 10, "Math formulas")
    bar._active = True
    bar._current = 5
    bar._render("Math formulas")
    # no exception; bar uses in-place render

"""Terminal output for the notion2tex CLI (colors and progress when supported)."""

from __future__ import annotations

import itertools
import os
import sys
import threading
import time
from typing import Iterator, TextIO, TypeVar

T = TypeVar("T")

_BAR_WIDTH = 28
_SPINNER_FRAMES = "|/-\\"


def _supports_color(stream: TextIO | None = None) -> bool:
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("FORCE_COLOR") == "1":
        return True
    return hasattr(stream, "isatty") and stream.isatty()


class _ProgressBar:
    """In-place progress bar (disabled when stdout is not a TTY)."""

    def __init__(self, console: Console, total: int, label: str) -> None:
        self._console = console
        self._total = max(1, total)
        self._label = label
        self._current = 0
        self._active = console.progress_enabled

    def advance(self, n: int = 1, *, sublabel: str | None = None) -> None:
        self._current = min(self._total, self._current + n)
        if not self._active:
            if self._current >= self._total:
                self._console.detail(f"{self._label} — done")
            return
        step = max(1, self._total // 40)
        if (
            self._current >= self._total
            or self._current <= n
            or self._current % step == 0
        ):
            self._render(sublabel or self._label)

    def _render(self, sublabel: str) -> None:
        ratio = self._current / self._total
        filled = int(_BAR_WIDTH * ratio)
        bar = "█" * filled + "░" * (_BAR_WIDTH - filled)
        pct = f"{int(ratio * 100):>3}%"
        text = f"      {sublabel[:32]:<32} [{bar}] {pct}"
        if self._console._color:
            text = self._console._style("2", text)
        sys.stdout.write("\r" + text)
        sys.stdout.flush()

    def finish(self, message: str | None = None) -> None:
        if self._active:
            self._current = self._total
            self._render(message or self._label)
            sys.stdout.write("\n")
            sys.stdout.flush()
        elif message:
            self._console.detail(message)


class _TaskSpinner:
    """Spinner for steps without a known progress total (e.g. pandoc)."""

    def __init__(self, console: Console, label: str) -> None:
        self._console = console
        self._label = label
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> _TaskSpinner:
        if not self._console.progress_enabled:
            self._console.detail(self._label)
            return self
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *args: object) -> None:
        if not self._console.progress_enabled:
            return
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        sys.stdout.write("\r" + " " * 72 + "\r")
        sys.stdout.flush()

    def _spin(self) -> None:
        for frame in itertools.cycle(_SPINNER_FRAMES):
            if self._stop.is_set():
                break
            line = f"      {self._label} {frame}"
            if self._console._color:
                line = self._console._style("2", line)
            sys.stdout.write("\r" + line)
            sys.stdout.flush()
            time.sleep(0.08)


class Console:
    """Structured, concise CLI messages in English."""

    def __init__(self, *, color: bool | None = None, progress: bool | None = None) -> None:
        tty = _supports_color()
        self._color = tty if color is None else color
        self._progress = tty if progress is None else progress

    @property
    def progress_enabled(self) -> bool:
        return self._progress

    def configure(self, *, color: bool, progress: bool | None = None) -> None:
        self._color = color
        if progress is None:
            self._progress = color and _supports_color()
        else:
            self._progress = progress and _supports_color()

    def _style(self, code: str, text: str, *, stream: TextIO | None = None) -> str:
        if not self._color:
            return text
        reset = "\033[0m"
        if stream is sys.stderr:
            return f"\033[{code}m{text}{reset}"
        return f"\033[{code}m{text}{reset}"

    def banner(self, *, input_path: str, page: str | None = None) -> None:
        title = self._style("1;36", "notion2tex")
        print(f"{title}  Notion export → PDF\n")
        print(f"  {'Input:':<8} {input_path}")
        if page:
            print(f"  {'Page:':<8} {page}")
        print()

    def step(self, current: int, total: int, title: str) -> None:
        label = self._style("1", f"[{current}/{total}] {title}")
        print(label)

    def detail(self, message: str) -> None:
        line = self._style("2", f"      {message}")
        print(line)

    def progress(self, total: int, label: str) -> _ProgressBar:
        return _ProgressBar(self, total, label)

    def task(self, label: str) -> _TaskSpinner:
        return _TaskSpinner(self, label)

    def track(
        self, iterable: Iterator[T], total: int, label: str
    ) -> Iterator[T]:
        bar = self.progress(total, label)
        for item in iterable:
            yield item
            bar.advance()
        bar.finish()

    def success(self, message: str) -> None:
        mark = self._style("32", "✓")
        print(f"{mark} {message}")

    def warn(self, message: str) -> None:
        mark = self._style("33", "!", stream=sys.stderr)
        print(f"{mark} {message}", file=sys.stderr)

    def error(self, message: str) -> None:
        mark = self._style("31", "✗", stream=sys.stderr)
        print(f"{mark} {message}", file=sys.stderr)


console = Console()

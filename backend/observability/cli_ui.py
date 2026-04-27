from __future__ import annotations

import atexit
import os
import sys
import threading
import time
from contextlib import contextmanager
from typing import Any, Iterator

try:
    from tqdm.auto import tqdm as _tqdm  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - optional dependency at runtime
    _tqdm = None

_BAR_FORMAT = (
    "{desc:<18} {percentage:3.0f}%|{bar:36}| {n_fmt}/{total_fmt} {unit} "
    "[{elapsed}<{remaining}, {rate_fmt}]"
)
_ANSI_RESET = "\x1b[0m"
_PROGRESS_AREA_READY = False
_SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
_SPINNER_INTERVAL_SECONDS = 0.8
_CURSOR_HIDE = "\x1b[?25l"
_CURSOR_SHOW = "\x1b[?25h"
_ACTIVE_PROGRESS_BARS = 0
_CURSOR_HIDDEN = False
_CURSOR_LOCK = threading.Lock()


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


class _SpinnerProgress:
    def __init__(self, *, bar: Any, desc: str) -> None:
        self._bar = bar
        self._desc = desc
        self._frame_index = 0
        self._last_frame_update = time.monotonic()
        self._set_desc_frame()

    def _set_desc_frame(self) -> None:
        frame = _SPINNER_FRAMES[self._frame_index % len(_SPINNER_FRAMES)]
        self._bar.set_description_str(f"{frame} {self._desc}")

    def _advance_frame_if_due(self) -> None:
        now = time.monotonic()
        if now - self._last_frame_update < _SPINNER_INTERVAL_SECONDS:
            return
        self._last_frame_update = now
        self._frame_index = (self._frame_index + 1) % len(_SPINNER_FRAMES)
        self._set_desc_frame()

    def update(self, n: int = 1) -> Any:
        self._advance_frame_if_due()
        return self._bar.update(n)

    def close(self) -> Any:
        try:
            return self._bar.close()
        finally:
            _release_progress_cursor()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._bar, name)


def _is_non_interactive_env() -> bool:
    if _env_flag("PROGRESS_FORCE_TTY"):
        return False
    if os.getenv("CI") or os.getenv("NO_COLOR"):
        return True
    return not sys.stderr.isatty()


def _supports_ansi_color() -> bool:
    if _is_non_interactive_env():
        return False
    return os.getenv("TERM", "").lower() != "dumb"


def _bar_colour_prefix(stage: str | None) -> str:
    if stage == "raw":
        # Muted steel-blue for raw-stage bars.
        return os.getenv("PROGRESS_BAR_ANSI_RAW", "\x1b[38;5;67m")
    if stage == "normalized":
        # Muted teal for normalized-stage bars.
        return os.getenv("PROGRESS_BAR_ANSI_NORMALIZED", "\x1b[38;5;72m")
    return ""


def _set_cursor_visible(*, visible: bool) -> None:
    if _is_non_interactive_env() or not _supports_ansi_color():
        return
    sys.stderr.write(_CURSOR_SHOW if visible else _CURSOR_HIDE)
    sys.stderr.flush()


def _acquire_progress_cursor() -> None:
    global _ACTIVE_PROGRESS_BARS, _CURSOR_HIDDEN
    with _CURSOR_LOCK:
        _ACTIVE_PROGRESS_BARS += 1
        if _CURSOR_HIDDEN:
            return
        _set_cursor_visible(visible=False)
        _CURSOR_HIDDEN = True


def _release_progress_cursor() -> None:
    global _ACTIVE_PROGRESS_BARS, _CURSOR_HIDDEN
    with _CURSOR_LOCK:
        if _ACTIVE_PROGRESS_BARS > 0:
            _ACTIVE_PROGRESS_BARS -= 1
        if _ACTIVE_PROGRESS_BARS > 0 or not _CURSOR_HIDDEN:
            return
        _set_cursor_visible(visible=True)
        _CURSOR_HIDDEN = False


def _restore_cursor_on_exit() -> None:
    global _ACTIVE_PROGRESS_BARS, _CURSOR_HIDDEN
    with _CURSOR_LOCK:
        _ACTIVE_PROGRESS_BARS = 0
        if not _CURSOR_HIDDEN:
            return
        _set_cursor_visible(visible=True)
        _CURSOR_HIDDEN = False


def _init_progress_area(enabled: bool) -> int:
    global _PROGRESS_AREA_READY
    if not enabled or _tqdm is None or _is_non_interactive_env():
        return 0
    if _PROGRESS_AREA_READY:
        return 1
    _tqdm.write("")
    _tqdm.write("─" * 72)
    _PROGRESS_AREA_READY = True
    return 1


def create_progress(
    *,
    total: int | None,
    desc: str,
    unit: str,
    enabled: bool,
    leave: bool = True,
    stage: str | None = None,
    footer: bool = False,
    position: int | None = None,
) -> Any | None:
    if not enabled or _tqdm is None or _is_non_interactive_env():
        return None
    if footer:
        base_pos = _init_progress_area(enabled=enabled)
        if position is None:
            position = base_pos
    if position is None:
        position = 0
    bar_format = _BAR_FORMAT if total is not None else None
    if bar_format and _supports_ansi_color():
        prefix = _bar_colour_prefix(stage)
        if prefix:
            bar_format = bar_format.replace("{bar:36}", f"{prefix}{{bar:36}}{_ANSI_RESET}")
    bar = _tqdm(
        total=total,
        desc=desc,
        unit=unit,
        leave=leave,
        dynamic_ncols=True,
        mininterval=0.8,
        smoothing=0.1,
        bar_format=bar_format,
        position=position,
    )
    _acquire_progress_cursor()
    return _SpinnerProgress(bar=bar, desc=desc)


def progress_write(message: str, enabled: bool) -> None:
    if enabled and _tqdm is not None:
        _tqdm.write(message)
    else:
        print(message)


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, rem = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m {rem:.1f}s"
    hours, rem_m = divmod(minutes, 60)
    return f"{int(hours)}h {int(rem_m)}m {rem:.1f}s"


@contextmanager
def timed_step(label: str, *, enabled: bool = True) -> Iterator[None]:
    started = time.perf_counter()
    if enabled:
        progress_write(f"[start] {label}", enabled=enabled)
    try:
        yield
    finally:
        if enabled:
            elapsed = time.perf_counter() - started
            progress_write(f"[done]  {label} in {format_duration(elapsed)}", enabled=enabled)


atexit.register(_restore_cursor_on_exit)

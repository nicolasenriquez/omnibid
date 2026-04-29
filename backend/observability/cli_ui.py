from __future__ import annotations

import atexit
import os
import sys
import threading
import time
from contextlib import contextmanager
from typing import Any, Iterator

try:
    from rich.console import Console as _Console
    from rich.progress import (
        BarColumn,
        SpinnerColumn,
        TextColumn,
    )
    from rich.progress import (
        Progress as _RichProgress,
    )
except ImportError:  # pragma: no cover - optional dependency at runtime
    _RichProgress = None  # type: ignore[assignment,misc]
    _Console = None  # type: ignore[assignment,misc]

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
_CURSOR_HIDE = "\x1b[?25l"
_CURSOR_SHOW = "\x1b[?25h"
_ACTIVE_PROGRESS_BARS = 0
_CURSOR_HIDDEN = False
_CURSOR_LOCK = threading.Lock()

# Shared rich console instance (stderr for progress output).
_console: _Console | None = None


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


class _RichProgressWrapper:
    """Wraps a rich.progress.Progress + task to match the existing tqdm-like API.

    Consumers call ``update(n)``, ``close()``, and ``set_description_str()``
    exactly as they did with the old ``_SpinnerProgress`` wrapper.
    """

    def __init__(self, *, progress: Any, task_id: Any, desc: str) -> None:
        self._progress = progress
        self._task_id = task_id
        self._desc = desc
        self._progress.update(task_id, description=desc)

    def update(self, n: int = 1) -> None:
        self._progress.advance(self._task_id, advance=n)

    def close(self) -> None:
        try:
            self._progress.remove_task(self._task_id)
        finally:
            _release_progress_cursor()

    def set_description_str(self, desc: str) -> None:
        self._progress.update(self._task_id, description=desc)

    def __getattr__(self, name: str) -> Any:
        # Fallback for any tqdm attributes consumers might still access.
        raise AttributeError(f"_RichProgressWrapper has no attribute {name!r}")


class _TqdmProgressWrapper:
    def __init__(self, *, bar: Any) -> None:
        self._bar = bar

    def update(self, n: int = 1) -> Any:
        return self._bar.update(n)

    def close(self) -> Any:
        try:
            return self._bar.close()
        finally:
            _release_progress_cursor()

    def set_description_str(self, desc: str) -> None:
        self._bar.set_description_str(desc)

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


def _bar_colour_style(stage: str | None) -> str:
    if stage == "raw":
        return os.getenv("PROGRESS_BAR_ANSI_RAW", "steel_blue")
    if stage == "normalized":
        return os.getenv("PROGRESS_BAR_ANSI_NORMALIZED", "dark_cyan")
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
    if not enabled or _RichProgress is None or _is_non_interactive_env():
        return 0
    if _PROGRESS_AREA_READY:
        return 1
    _console_print("")
    _console_print("─" * 72)
    _PROGRESS_AREA_READY = True
    return 1


def _init_tqdm_progress_area(enabled: bool) -> int:
    global _PROGRESS_AREA_READY
    if not enabled or _tqdm is None or _is_non_interactive_env():
        return 0
    if _PROGRESS_AREA_READY:
        return 1
    _tqdm.write("")
    _tqdm.write("-" * 72)
    _PROGRESS_AREA_READY = True
    return 1


def _console_print(message: str) -> None:
    """Print to the shared rich console, or fall back to stderr."""
    if _Console is not None and _console is not None:
        _console.print(message)
    else:
        print(message, file=sys.stderr)


def _make_rich_columns(*, total: int | None, stage: str | None) -> list:
    """Build rich.progress columns matching the existing bar format."""
    columns: list = [
        SpinnerColumn(spinner_name="dots", style="grey46"),
        TextColumn("{task.description:<18}"),
    ]
    if total is not None:
        columns.append(TextColumn("{task.percentage:>3.0f}%"))
        bar_style = _bar_colour_style(stage)
        if bar_style and _supports_ansi_color():
            columns.append(BarColumn(bar_width=36, style=bar_style, pulse_style=bar_style))
        else:
            columns.append(BarColumn(bar_width=36))
        columns.append(
            TextColumn(" {task.completed}/{task.total} {task.fields[unit]}"),
        )
        columns.append(
            TextColumn(" [{task.elapsed}<{task.remaining}]"),
        )
    return columns


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
    if not enabled or _is_non_interactive_env():
        return None
    if position is not None:
        if _tqdm is None:
            return None
        if footer:
            _init_tqdm_progress_area(enabled=enabled)
        bar = _tqdm(
            total=total,
            desc=desc,
            unit=unit,
            leave=leave,
            dynamic_ncols=True,
            mininterval=0.8,
            smoothing=0.1,
            bar_format=_BAR_FORMAT if total is not None else None,
            position=position,
        )
        _acquire_progress_cursor()
        return _TqdmProgressWrapper(bar=bar)
    if _RichProgress is None:
        return None
    if footer:
        _init_progress_area(enabled=enabled)
    columns = _make_rich_columns(total=total, stage=stage)
    progress = _RichProgress(
        *columns,
        transient=not leave,
        console=_console,
    )
    progress.start()
    task_id = progress.add_task(
        description=desc,
        total=total,
        unit=unit,
    )
    _acquire_progress_cursor()
    return _RichProgressWrapper(progress=progress, task_id=task_id, desc=desc)


def progress_write(message: str, enabled: bool) -> None:
    if enabled and _Console is not None and _console is not None:
        _console.print(message)
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


# --- Module-level initialisation ---


def _init_console() -> None:
    global _console
    if _Console is not None and _console is None:
        _console = _Console(stderr=True, highlight=False)


_init_console()
atexit.register(_restore_cursor_on_exit)

from __future__ import annotations

import os
import sys
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


def _is_non_interactive_env() -> bool:
    if os.getenv("CI") or os.getenv("NO_COLOR"):
        return True
    return not sys.stderr.isatty()


def _supports_ansi_color() -> bool:
    if _is_non_interactive_env():
        return False
    return os.getenv("TERM", "").lower() != "dumb"


def _bar_colour_prefix(stage: str | None) -> str:
    if stage == "raw":
        return os.getenv("PROGRESS_BAR_ANSI_RAW", "\x1b[38;5;45m")
    if stage == "normalized":
        return os.getenv("PROGRESS_BAR_ANSI_NORMALIZED", "\x1b[38;5;33m")
    return ""


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
    return _tqdm(
        total=total,
        desc=desc,
        unit=unit,
        leave=leave,
        dynamic_ncols=True,
        mininterval=0.2,
        smoothing=0.1,
        bar_format=bar_format,
        position=position,
    )


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

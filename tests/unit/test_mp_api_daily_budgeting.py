from __future__ import annotations

import pytest

from backend.pipeline.orchestration.daily_pipeline import _resolve_rolling_window_days_for_sync


def test_resolve_rolling_window_days_without_budget_cap() -> None:
    assert _resolve_rolling_window_days_for_sync(window_days=4, max_requests=None) == 4


def test_resolve_rolling_window_days_reserves_detail_budget_when_capped() -> None:
    assert _resolve_rolling_window_days_for_sync(window_days=4, max_requests=4) == 3
    assert _resolve_rolling_window_days_for_sync(window_days=4, max_requests=2) == 1
    assert _resolve_rolling_window_days_for_sync(window_days=2, max_requests=4) == 2


def test_resolve_rolling_window_days_handles_single_request_budget() -> None:
    assert _resolve_rolling_window_days_for_sync(window_days=4, max_requests=1) == 1


def test_resolve_rolling_window_days_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="window_days must be >= 1"):
        _resolve_rolling_window_days_for_sync(window_days=0, max_requests=3)

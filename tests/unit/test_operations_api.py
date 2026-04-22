from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from backend.api.deps import get_db
from backend.api.routers import operations
from backend.main import app


class _DummyResult:
    def __init__(
        self,
        *,
        rows: list[Any] | None = None,
        scalar: int | None = None,
    ) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def scalars(self) -> "_DummyResult":
        return self

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self._rows)

    def scalar_one(self) -> int:
        if self._scalar is None:
            raise AssertionError("scalar_one requested but no scalar value was configured")
        return self._scalar

    def scalar_one_or_none(self) -> Any:
        return self._rows[0] if self._rows else None


class _DummySession:
    def __init__(self, responses: list[_DummyResult | Exception]) -> None:
        self._responses = responses
        self.execute_calls = 0
        self.rollback_calls = 0

    def execute(self, _stmt: object) -> _DummyResult:
        if not self._responses:
            raise AssertionError("no dummy response available for execute call")
        self.execute_calls += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def rollback(self) -> None:
        self.rollback_calls += 1


@pytest.fixture(autouse=True)
def _reset_router_state() -> None:
    app.dependency_overrides.clear()
    operations.reset_datasets_summary_cache()
    yield
    app.dependency_overrides.clear()
    operations.reset_datasets_summary_cache()


def _set_db_override(session: _DummySession) -> None:
    def _override_get_db():  # type: ignore[no-untyped-def]
        yield session

    app.dependency_overrides[get_db] = _override_get_db


def test_list_runs_rejects_limit_below_range() -> None:
    session = _DummySession([])
    _set_db_override(session)

    with TestClient(app) as client:
        response = client.get("/runs", params={"limit": 0})

    assert response.status_code == 422
    assert session.execute_calls == 0


def test_list_files_rejects_limit_above_range() -> None:
    session = _DummySession([])
    _set_db_override(session)

    with TestClient(app) as client:
        response = client.get("/files", params={"limit": 201})

    assert response.status_code == 422
    assert session.execute_calls == 0


def test_list_runs_accepts_bounded_limit() -> None:
    run_row = SimpleNamespace(
        id=uuid4(),
        run_key="run-key",
        dataset_type="licitacion",
        status="completed",
        started_at=None,
        finished_at=None,
        source_file_id=None,
    )
    session = _DummySession([_DummyResult(rows=[run_row])])
    _set_db_override(session)

    with TestClient(app) as client:
        response = client.get("/runs", params={"limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["run_key"] == "run-key"
    assert session.execute_calls == 1


def test_datasets_summary_cached_mode_reuses_cache() -> None:
    responses = [_DummyResult(scalar=value) for value in [1, 2, 3, 4, 5, 6, 7, 8]]
    session = _DummySession(responses)
    _set_db_override(session)

    with TestClient(app) as client:
        first = client.get("/datasets/summary", params={"mode": "cached", "max_age_seconds": 300})
        second = client.get("/datasets/summary", params={"mode": "cached", "max_age_seconds": 300})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["summary_meta"]["strategy"] == "ttl_cached_full_counts"
    assert first.json()["summary_meta"]["is_cached"] is False
    assert second.json()["summary_meta"]["is_cached"] is True
    assert (
        second.json()["summary_meta"]["precomputed_summary_storage"]
        == "deferred_followup_proposal_required"
    )
    assert session.execute_calls == 8


def test_datasets_summary_fresh_mode_recomputes_counts() -> None:
    responses = [_DummyResult(scalar=value) for value in [1] * 16]
    session = _DummySession(responses)
    _set_db_override(session)

    with TestClient(app) as client:
        first = client.get("/datasets/summary", params={"mode": "fresh", "max_age_seconds": 300})
        second = client.get("/datasets/summary", params={"mode": "fresh", "max_age_seconds": 300})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["summary_meta"]["is_cached"] is False
    assert second.json()["summary_meta"]["is_cached"] is False
    assert session.execute_calls == 16


def test_datasets_summary_cached_mode_does_not_cache_partial_payloads() -> None:
    responses: list[_DummyResult | Exception] = [RuntimeError("transient count failure")]
    responses.extend(_DummyResult(scalar=value) for value in [2, 3, 4, 5, 6, 7, 8])
    responses.extend(_DummyResult(scalar=value) for value in [10, 20, 30, 40, 50, 60, 70, 80])
    session = _DummySession(responses)
    _set_db_override(session)

    with TestClient(app) as client:
        first = client.get("/datasets/summary", params={"mode": "cached", "max_age_seconds": 300})
        second = client.get("/datasets/summary", params={"mode": "cached", "max_age_seconds": 300})
        third = client.get("/datasets/summary", params={"mode": "cached", "max_age_seconds": 300})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200
    assert first.json()["source_files"] is None
    assert second.json()["source_files"] == 10
    assert first.json()["summary_meta"]["is_cached"] is False
    assert second.json()["summary_meta"]["is_cached"] is False
    assert third.json()["summary_meta"]["is_cached"] is True
    assert session.execute_calls == 16
    assert session.rollback_calls == 1

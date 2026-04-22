from __future__ import annotations

from datetime import UTC, datetime
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
        self.add_calls = 0
        self.commit_calls = 0
        self.refresh_calls = 0

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

    def add(self, _obj: object) -> None:
        self.add_calls += 1

    def commit(self) -> None:
        self.commit_calls += 1

    def refresh(self, obj: Any) -> None:
        self.refresh_calls += 1
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        if getattr(obj, "generated_at", None) is None:
            obj.generated_at = datetime.now(UTC)


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


def _snapshot_row(source_files_count: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        generated_at=datetime.now(UTC),
        refresh_mode="fresh",
        status="success",
        source_files_count=source_files_count,
        raw_licitaciones_count=2,
        raw_ordenes_compra_count=3,
        normalized_licitaciones_count=4,
        normalized_licitacion_items_count=5,
        normalized_ofertas_count=6,
        normalized_ordenes_compra_count=7,
        normalized_ordenes_compra_items_count=8,
    )


def test_datasets_summary_cached_mode_uses_persisted_snapshot() -> None:
    snapshot = _snapshot_row(source_files_count=21)
    session = _DummySession([_DummyResult(rows=[snapshot])])
    _set_db_override(session)

    with TestClient(app) as client:
        response = client.get("/datasets/summary", params={"mode": "cached", "max_age_seconds": 300})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_files"] == 21
    assert payload["summary_meta"]["strategy"] == "persisted_success_snapshot"
    assert payload["summary_meta"]["precomputed_summary_storage"] == "enabled"
    assert payload["summary_meta"]["refresh_status"] == "not_requested"
    assert session.execute_calls == 1
    assert session.add_calls == 0


def test_datasets_summary_fresh_mode_persists_snapshot() -> None:
    responses: list[_DummyResult | Exception] = [_DummyResult(rows=[])]
    responses.extend(_DummyResult(scalar=value) for value in [10, 20, 30, 40, 50, 60, 70, 80])
    session = _DummySession(responses)
    _set_db_override(session)

    with TestClient(app) as client:
        response = client.get("/datasets/summary", params={"mode": "fresh", "max_age_seconds": 300})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_files"] == 10
    assert payload["summary_meta"]["refresh_status"] == "refreshed"
    assert payload["summary_meta"]["snapshot_refresh_mode"] == "fresh"
    assert session.execute_calls == 9
    assert session.add_calls == 1
    assert session.commit_calls == 1
    assert session.rollback_calls == 0


def test_datasets_summary_fresh_mode_failure_falls_back_to_last_snapshot() -> None:
    snapshot = _snapshot_row(source_files_count=77)
    session = _DummySession(
        [
            _DummyResult(rows=[snapshot]),
            RuntimeError("count failed"),
            _DummyResult(rows=[snapshot]),
        ]
    )
    _set_db_override(session)

    with TestClient(app) as client:
        response = client.get("/datasets/summary", params={"mode": "fresh", "max_age_seconds": 300})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_files"] == 77
    assert payload["summary_meta"]["refresh_status"] == "failed_using_last_successful_snapshot"
    assert payload["summary_meta"]["refresh_error"] == "RuntimeError"
    assert session.execute_calls == 3
    assert session.rollback_calls == 1
    assert session.add_calls == 0

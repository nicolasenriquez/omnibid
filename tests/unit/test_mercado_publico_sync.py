from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from backend.integrations.mercado_publico.errors import (
    MercadoPublicoContractDriftError,
    MercadoPublicoRequestError,
)
from backend.integrations.mercado_publico.schemas import parse_licitaciones_response
from backend.integrations.mercado_publico.sync import (
    SyncSummary,
    create_sync_run,
    execute_sync_mode,
    mark_sync_run_completed,
    mark_sync_run_failed,
    rolling_window_dates,
)


def _patch_runtime_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.integrations.mercado_publico.sync._acquire_scoped_lock",
        lambda *_args, **_kwargs: 1,
    )
    monkeypatch.setattr(
        "backend.integrations.mercado_publico.sync._release_scoped_lock",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "backend.integrations.mercado_publico.sync.reserve_request_budget",
        lambda *_args, **_kwargs: None,
    )


def _response_with_codes(*codes: str):
    return parse_licitaciones_response(_raw_payload_with_codes(*codes))


def _raw_payload_with_codes(*codes: str) -> dict[str, Any]:
    return {
        "Version": "v1",
        "Cantidad": len(codes),
        "FechaCreacion": "08052026",
        "Listado": [
            {
                "CodigoExterno": code,
                "Nombre": f"Licitacion {code}",
                "CodigoEstado": 5,
                "Estado": "Publicada",
                "FechaPublicacion": "08052026",
            }
            for code in codes
        ],
    }


def test_rolling_window_dates_returns_t_to_t_minus_n() -> None:
    days = rolling_window_dates(anchor_day=date(2026, 5, 8), window_days=4)
    assert days == [
        date(2026, 5, 8),
        date(2026, 5, 7),
        date(2026, 5, 6),
        date(2026, 5, 5),
    ]


def test_execute_sync_mode_active_discovery_persists_one_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    _patch_runtime_guards(monkeypatch)

    class _SessionWithExecute:
        def execute(self, *_args, **_kwargs):
            return None

    class FakeClient:
        settings = SimpleNamespace(daily_request_limit=10000)

        def fetch_active_discovery_with_raw(self):
            raw = _raw_payload_with_codes("100-1-LR26", "100-2-LR26")
            return raw, parse_licitaciones_response(raw)

        def build_active_discovery_params(self):
            return {"estado": "activas", "ticket": "secret"}

        def build_safe_url(self, *, endpoint: str, params: dict[str, str]) -> str:
            return f"https://example.invalid/{endpoint}?{params.get('estado', '')}"

    def fake_persist_notice_batch(*args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            notices_skipped_missing_external_notice_code=0,
            snapshots_upserted=2,
            snapshots_inserted=2,
            snapshots_updated=0,
        )

    monkeypatch.setattr("backend.integrations.mercado_publico.sync.persist_notice_batch", fake_persist_notice_batch)

    summary = execute_sync_mode(
        session=_SessionWithExecute(),  # type: ignore[arg-type]
        client=FakeClient(),  # type: ignore[arg-type]
        pipeline_run_id=uuid4(),
        mode="active-discovery",
    )

    assert summary.requests == 1
    assert summary.notices_seen == 2
    assert summary.notices_skipped_missing_external_notice_code == 0
    assert summary.snapshots_upserted == 2
    assert summary.snapshots_inserted == 2
    assert summary.snapshots_updated == 0
    assert calls[0]["resource_key"] == "estado=activas"
    assert calls[0]["requested_at"] is not None
    payload = calls[0]["payload"]
    assert payload["Version"] == "v1"
    assert "Codigo" not in payload
    assert "Descripcion" not in payload


def test_execute_sync_mode_rolling_window_handles_empty_result(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = {"value": 0}
    _patch_runtime_guards(monkeypatch)

    class FakeClient:
        settings = SimpleNamespace(daily_request_limit=10000)

        def fetch_rolling_window_with_raw(self, *, day: date, estado: str | None = None):
            _ = day, estado
            call_count["value"] += 1
            raw = _raw_payload_with_codes()
            return raw, parse_licitaciones_response(raw)

        def build_rolling_window_params(self, *, day: date, estado: str | None = None):
            params = {"fecha": day.strftime("%d%m%Y"), "ticket": "secret"}
            if estado is not None:
                params["estado"] = estado
            return params

        def build_safe_url(self, *, endpoint: str, params: dict[str, str]) -> str:
            return f"https://example.invalid/{endpoint}?{params.get('fecha', '')}"

    def fake_persist_notice_batch(*args, **kwargs):
        _ = args, kwargs
        return SimpleNamespace(
            notices_skipped_missing_external_notice_code=0,
            snapshots_upserted=0,
            snapshots_inserted=0,
            snapshots_updated=0,
        )

    monkeypatch.setattr("backend.integrations.mercado_publico.sync.persist_notice_batch", fake_persist_notice_batch)

    summary = execute_sync_mode(
        session=object(),  # type: ignore[arg-type]
        client=FakeClient(),  # type: ignore[arg-type]
        pipeline_run_id=uuid4(),
        mode="rolling-window",
        anchor_day=date(2026, 5, 8),
        window_days=4,
    )

    assert call_count["value"] == 4
    assert summary.requests == 4
    assert summary.notices_seen == 0
    assert summary.notices_skipped_missing_external_notice_code == 0
    assert summary.snapshots_upserted == 0
    assert summary.snapshots_inserted == 0
    assert summary.snapshots_updated == 0


def test_execute_sync_mode_detail_by_codigo_requires_codes() -> None:
    with pytest.raises(ValueError, match="requires at least one codigo"):
        execute_sync_mode(
            session=object(),  # type: ignore[arg-type]
            client=object(),  # type: ignore[arg-type]
            pipeline_run_id=uuid4(),
            mode="detail-by-codigo",
            codigos=[],
        )


def test_execute_sync_mode_detail_by_codigo_iterates_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    _patch_runtime_guards(monkeypatch)

    class FakeClient:
        settings = SimpleNamespace(daily_request_limit=10000)

        def fetch_detail_by_codigo_with_raw(self, *, codigo: str):
            seen.append(codigo)
            raw = _raw_payload_with_codes(codigo)
            return raw, parse_licitaciones_response(raw)

        def build_detail_by_codigo_params(self, *, codigo: str):
            return {"codigo": codigo, "ticket": "secret"}

        def build_safe_url(self, *, endpoint: str, params: dict[str, str]) -> str:
            return f"https://example.invalid/{endpoint}?{params.get('codigo', '')}"

    def fake_persist_notice_batch(*args, **kwargs):
        _ = args, kwargs
        return SimpleNamespace(
            notices_skipped_missing_external_notice_code=0,
            snapshots_upserted=1,
            snapshots_inserted=1,
            snapshots_updated=0,
        )

    monkeypatch.setattr("backend.integrations.mercado_publico.sync.persist_notice_batch", fake_persist_notice_batch)

    summary = execute_sync_mode(
        session=object(),  # type: ignore[arg-type]
        client=FakeClient(),  # type: ignore[arg-type]
        pipeline_run_id=uuid4(),
        mode="detail-by-codigo",
        codigos=["1274285-76-LR25", "2000000-10-LQ26"],
    )

    assert seen == ["1274285-76-LR25", "2000000-10-LQ26"]
    assert summary.requests == 2
    assert summary.notices_seen == 2
    assert summary.notices_skipped_missing_external_notice_code == 0
    assert summary.snapshots_upserted == 2
    assert summary.snapshots_inserted == 2
    assert summary.snapshots_updated == 0


def test_execute_sync_mode_propagates_retry_exhaustion_error() -> None:
    class FakeClient:
        settings = SimpleNamespace(daily_request_limit=10000)

        def build_active_discovery_params(self):
            return {"estado": "activas", "ticket": "secret"}

        def build_safe_url(self, *, endpoint: str, params: dict[str, str]) -> str:
            return f"https://example.invalid/{endpoint}?{params.get('estado', '')}"

        def fetch_active_discovery_with_raw(self):
            raise MercadoPublicoRequestError("retry budget exhausted")

    with pytest.raises(MercadoPublicoRequestError, match="retry budget exhausted"), pytest.MonkeyPatch.context() as mp:
        _patch_runtime_guards(mp)
        execute_sync_mode(
            session=object(),  # type: ignore[arg-type]
            client=FakeClient(),  # type: ignore[arg-type]
            pipeline_run_id=uuid4(),
            mode="active-discovery",
        )


def test_execute_sync_mode_propagates_contract_drift_error() -> None:
    class FakeClient:
        settings = SimpleNamespace(daily_request_limit=10000)

        def build_active_discovery_params(self):
            return {"estado": "activas", "ticket": "secret"}

        def build_safe_url(self, *, endpoint: str, params: dict[str, str]) -> str:
            return f"https://example.invalid/{endpoint}?{params.get('estado', '')}"

        def fetch_active_discovery_with_raw(self):
            raise MercadoPublicoContractDriftError("unexpected shape")

    with pytest.raises(MercadoPublicoContractDriftError, match="unexpected shape"), pytest.MonkeyPatch.context() as mp:
        _patch_runtime_guards(mp)
        execute_sync_mode(
            session=object(),  # type: ignore[arg-type]
            client=FakeClient(),  # type: ignore[arg-type]
            pipeline_run_id=uuid4(),
            mode="active-discovery",
        )


class _FakeLifecycleSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        for value in self.added:
            if getattr(value, "id", None) is None:
                setattr(value, "id", uuid4())


def test_create_sync_run_sets_running_lifecycle_metadata() -> None:
    session = _FakeLifecycleSession()
    run, step = create_sync_run(
        session,  # type: ignore[arg-type]
        mode="rolling-window",
        requested_by="github_actions",
        run_parameters={"window_days": 4},
        config={"window_days": 4},
    )

    assert run.status == "running"
    assert run.provider == "mercado_publico"
    assert run.run_mode == "rolling-window"
    assert run.requested_by == "github_actions"
    assert run.run_stats_json["final_status"] == "running"
    assert step.status == "running"
    assert step.step_name == "mp_api_rolling_refresh"


def test_mark_sync_run_completed_sets_succeeded_stats() -> None:
    run = SimpleNamespace(
        status="running",
        config={"window_days": 4},
        run_stats_json={},
        error_summary=None,
    )
    step = SimpleNamespace(status="running", rows_in=0, rows_out=0, rows_rejected=0, error_details=None)
    summary = SyncSummary(
        mode="rolling-window",
        requests=4,
        notices_seen=8,
        notices_skipped_missing_external_notice_code=1,
        snapshots_upserted=7,
        snapshots_inserted=5,
        snapshots_updated=2,
    )

    mark_sync_run_completed(run=run, step=step, summary=summary)

    assert run.status == "completed"
    assert run.run_stats_json["final_status"] == "succeeded"
    assert run.config["sync_summary"]["mode"] == "rolling-window"
    assert step.status == "completed"
    assert step.rows_in == 4
    assert step.rows_out == 7
    assert step.rows_rejected == 1


def test_mark_sync_run_failed_sets_failed_stats() -> None:
    run = SimpleNamespace(status="running", run_stats_json={}, error_summary=None)
    step = SimpleNamespace(status="running", error_details=None)

    mark_sync_run_failed(run=run, step=step, error_message="lock contention")

    assert run.status == "failed"
    assert run.run_stats_json["final_status"] == "failed"
    assert run.error_summary == "lock contention"
    assert step.status == "failed"
    assert step.error_details["error"] == "lock contention"


def test_execute_sync_mode_fails_fast_on_lock_contention(monkeypatch: pytest.MonkeyPatch) -> None:
    fetch_calls = {"value": 0}

    class _SessionWithExecute:
        def execute(self, *_args, **_kwargs):
            return None

    class FakeClient:
        settings = SimpleNamespace(daily_request_limit=10000)

        def build_active_discovery_params(self):
            return {"estado": "activas", "ticket": "secret"}

        def fetch_active_discovery_with_raw(self):
            fetch_calls["value"] += 1
            raw = _raw_payload_with_codes("100-1-LR26")
            return raw, parse_licitaciones_response(raw)

    def _raise_lock(*_args, **_kwargs) -> int:
        raise RuntimeError("scoped advisory lock not available for key=mercado_publico:active_discovery")

    monkeypatch.setattr("backend.integrations.mercado_publico.sync._acquire_scoped_lock", _raise_lock)

    with pytest.raises(RuntimeError, match="scoped advisory lock not available"):
        execute_sync_mode(
            session=_SessionWithExecute(),  # type: ignore[arg-type]
            client=FakeClient(),  # type: ignore[arg-type]
            pipeline_run_id=uuid4(),
            mode="active-discovery",
        )

    assert fetch_calls["value"] == 0

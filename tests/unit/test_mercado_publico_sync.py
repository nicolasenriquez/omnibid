from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.integrations.mercado_publico.errors import (
    MercadoPublicoContractDriftError,
    MercadoPublicoRequestError,
)
from backend.integrations.mercado_publico.schemas import parse_licitaciones_response
from backend.integrations.mercado_publico.sync import execute_sync_mode, rolling_window_dates


def _response_with_codes(*codes: str):
    return parse_licitaciones_response(
        {
            "Codigo": 0,
            "Descripcion": "OK",
            "Cantidad": len(codes),
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
    )


def test_rolling_window_dates_returns_t_to_t_minus_n() -> None:
    days = rolling_window_dates(anchor_day=date(2026, 5, 8), window_days=4)
    assert days == [
        date(2026, 5, 8),
        date(2026, 5, 7),
        date(2026, 5, 6),
        date(2026, 5, 5),
    ]


def test_execute_sync_mode_active_discovery_persists_one_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeClient:
        def fetch_active_discovery(self):
            return _response_with_codes("100-1-LR26", "100-2-LR26")

        def build_active_discovery_params(self):
            return {"estado": "activas", "ticket": "secret"}

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
        session=object(),  # type: ignore[arg-type]
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


def test_execute_sync_mode_rolling_window_handles_empty_result(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = {"value": 0}

    class FakeClient:
        def fetch_rolling_window(self, *, day: date, estado: str | None = None):
            _ = day, estado
            call_count["value"] += 1
            return _response_with_codes()

        def build_rolling_window_params(self, *, day: date, estado: str | None = None):
            params = {"fecha": day.strftime("%d%m%Y"), "ticket": "secret"}
            if estado is not None:
                params["estado"] = estado
            return params

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

    class FakeClient:
        def fetch_detail_by_codigo(self, *, codigo: str):
            seen.append(codigo)
            return _response_with_codes(codigo)

        def build_detail_by_codigo_params(self, *, codigo: str):
            return {"codigo": codigo, "ticket": "secret"}

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
        def fetch_active_discovery(self):
            raise MercadoPublicoRequestError("retry budget exhausted")

    with pytest.raises(MercadoPublicoRequestError, match="retry budget exhausted"):
        execute_sync_mode(
            session=object(),  # type: ignore[arg-type]
            client=FakeClient(),  # type: ignore[arg-type]
            pipeline_run_id=uuid4(),
            mode="active-discovery",
        )


def test_execute_sync_mode_propagates_contract_drift_error() -> None:
    class FakeClient:
        def fetch_active_discovery(self):
            raise MercadoPublicoContractDriftError("unexpected shape")

    with pytest.raises(MercadoPublicoContractDriftError, match="unexpected shape"):
        execute_sync_mode(
            session=object(),  # type: ignore[arg-type]
            client=FakeClient(),  # type: ignore[arg-type]
            pipeline_run_id=uuid4(),
            mode="active-discovery",
        )

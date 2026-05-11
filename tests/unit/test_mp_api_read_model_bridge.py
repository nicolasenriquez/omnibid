from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

from backend.normalized import mp_api_read_model_bridge as bridge


class _ScalarIterableResult:
    def __init__(self, values):
        self._values = list(values)

    def scalars(self):
        return self

    def __iter__(self):
        return iter(self._values)


class _RowsResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)


class _QueuedSession:
    def __init__(self, queued_results):
        self._queued_results = list(queued_results)

    def execute(self, _statement):
        if not self._queued_results:
            raise AssertionError("unexpected execute() call with no queued result")
        return self._queued_results.pop(0)


def test_select_detail_enrichment_candidates_prefers_missing_or_stale_details() -> None:
    session = _QueuedSession(
        [
            _ScalarIterableResult(["A-1-LR26", "B-1-LR26", "C-1-LR26"]),
            _RowsResult(
                [
                    ("A-1-LR26", datetime(2026, 5, 9, 10, 0, 0)),
                    ("B-1-LR26", datetime(2026, 4, 20, 10, 0, 0)),
                ]
            ),
            _RowsResult(
                [
                    ("A-1-LR26", datetime(2026, 5, 18, 0, 0, 0)),
                    ("B-1-LR26", datetime(2026, 4, 30, 0, 0, 0)),
                ]
            ),
        ]
    )

    summary = bridge.select_detail_enrichment_candidates(
        session,  # type: ignore[arg-type]
        target_date=date(2026, 5, 10),
        pipeline_run_id=uuid4(),
        backfill_interval_days=7,
        max_candidates=1,
    )

    assert summary.notice_candidates == 3
    assert summary.detail_candidates == 2
    assert summary.selected_codes == ("B-1-LR26",)


def test_select_detail_enrichment_candidates_prioritizes_open_notices_even_when_recent() -> None:
    session = _QueuedSession(
        [
            _ScalarIterableResult(["OPEN-1", "CLOSED-1"]),
            _RowsResult(
                [
                    ("OPEN-1", datetime(2026, 5, 10, 10, 0, 0)),
                    ("CLOSED-1", datetime(2026, 5, 10, 10, 0, 0)),
                ]
            ),
            _RowsResult(
                [
                    ("OPEN-1", datetime(2026, 5, 16, 0, 0, 0)),
                    ("CLOSED-1", datetime(2026, 5, 8, 0, 0, 0)),
                ]
            ),
        ]
    )

    summary = bridge.select_detail_enrichment_candidates(
        session,  # type: ignore[arg-type]
        target_date=date(2026, 5, 11),
        pipeline_run_id=uuid4(),
        backfill_interval_days=7,
        max_candidates=None,
    )

    assert summary.notice_candidates == 2
    assert summary.detail_candidates == 1
    assert summary.selected_codes == ("OPEN-1",)


def test_canonicalize_payloads_uses_detail_last_and_expected_conflict_keys(
    monkeypatch,
) -> None:
    rolling_row = {
        "CodigoExterno": "1274285-76-LR25",
        "Codigo": "1274285",
        "Nombre": "Licitacion base",
        "Estado": "Publicada",
        "CodigoEstado": 5,
        "FechaPublicacion": "08052026",
        "FechaCierre": "10052026",
        "NumeroOferentes": None,
    }
    detail_row = {
        **rolling_row,
        "Descripcion": "Detalle enriquecido",
        "NumeroOferentes": 4,
        "Codigoitem": "1",
        "Correlativo": "1",
        "CodigoProveedor": "P-001",
        "RutProveedor": "11.111.111-1",
        "NombreProveedor": "Proveedor Uno",
        "Nombre de la Oferta": "Oferta Uno",
        "Estado Oferta": "Aceptada",
    }

    scoped_rows = [
        bridge._ScopedPayloadRow(  # noqa: SLF001
            payload_sha256="rolling-sha",
            row_index=0,
            raw_row=rolling_row,
            mode_rank=1,
            fetched_at=datetime(2026, 5, 10, 10, 0, 0),
        ),
        bridge._ScopedPayloadRow(  # noqa: SLF001
            payload_sha256="detail-sha",
            row_index=0,
            raw_row=detail_row,
            mode_rank=2,
            fetched_at=datetime(2026, 5, 10, 10, 5, 0),
        ),
    ]
    monkeypatch.setattr(
        bridge,
        "_select_scoped_payload_rows",
        lambda *_args, **_kwargs: scoped_rows,
    )

    captured_rows: dict[str, list[dict[str, object]]] = {}
    captured_conflicts: dict[str, list[str]] = {}

    def _fake_upsert_rows(_session, model, rows, conflict_fields):
        captured_rows[model.__name__] = list(rows)
        captured_conflicts[model.__name__] = list(conflict_fields)
        return len(rows)

    monkeypatch.setattr(bridge, "upsert_rows", _fake_upsert_rows)

    summary = bridge.canonicalize_mp_api_payloads_to_read_model(
        session=SimpleNamespace(),  # type: ignore[arg-type]
        source_file_id=uuid4(),
        pipeline_run_id=uuid4(),
    )

    assert summary.payload_rows_seen == 2
    assert summary.payload_rows_used == 2
    assert summary.notice_candidates == 1
    assert summary.upserted_notices == 2

    silver_notice_rows = captured_rows["SilverNotice"]
    assert len(silver_notice_rows) == 2
    assert silver_notice_rows[0]["notice_description_raw"] is None
    assert silver_notice_rows[1]["notice_description_raw"] == "Detalle enriquecido"
    assert captured_conflicts["SilverNotice"] == ["notice_id"]

    normalized_oferta_rows = captured_rows["NormalizedOferta"]
    assert normalized_oferta_rows[0]["supplier_key"] is not None
    assert captured_conflicts["NormalizedOferta"] == ["oferta_key_sha256"]

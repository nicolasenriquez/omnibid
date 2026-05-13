from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from backend.pipeline.transform import mp_api_read_model_bridge as bridge


class _ScalarIterableResult:
    def __init__(self, values):
        self._values = list(values)

    def scalars(self):
        return self

    def all(self):
        return list(self._values)

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
        self.statements = []

    def execute(self, _statement):
        self.statements.append(_statement)
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


def test_canonicalize_payloads_can_skip_normalized_upserts(monkeypatch) -> None:
    scoped_rows = [
        bridge._ScopedPayloadRow(  # noqa: SLF001
            payload_sha256="rolling-sha",
            row_index=0,
            raw_row={
                "CodigoExterno": "1274285-76-LR25",
                "Codigo": "1274285",
                "Nombre": "Licitacion base",
                "Estado": "Publicada",
                "CodigoEstado": 5,
                "FechaPublicacion": "08052026",
                "FechaCierre": "10052026",
            },
            mode_rank=1,
            fetched_at=datetime(2026, 5, 10, 10, 0, 0),
        )
    ]
    monkeypatch.setattr(
        bridge,
        "_select_scoped_payload_rows",
        lambda *_args, **_kwargs: scoped_rows,
    )

    touched_models: list[str] = []

    def _fake_upsert_rows(_session, model, rows, _conflict_fields):
        touched_models.append(model.__name__)
        return len(rows)

    monkeypatch.setattr(bridge, "upsert_rows", _fake_upsert_rows)

    summary = bridge.canonicalize_mp_api_payloads_to_read_model(
        session=SimpleNamespace(),  # type: ignore[arg-type]
        source_file_id=uuid4(),
        pipeline_run_id=uuid4(),
        include_normalized=False,
    )

    assert summary.upserted_normalized_licitaciones == 0
    assert summary.upserted_normalized_licitacion_items == 0
    assert "NormalizedLicitacion" not in touched_models
    assert "NormalizedLicitacionItem" not in touched_models


def test_api_detail_canonicalizes_to_normalized_licitaciones() -> None:
    snap = SimpleNamespace(
        external_notice_code="1274285-76-LR25",
        notice_id="1274285-76-LR25",
        notice_title="Servicio de soporte TI",
        description="Servicios de soporte informatico para sistemas criticos",
        official_status_code=5,
        official_status_name="Publicada",
        publication_date=date(2026, 5, 8),
        close_date=date(2026, 5, 18),
        buyer_org_code="ORG-001",
        buyer_org_name="Municipalidad X",
        buyer_unit_code="U-10",
        buyer_unit_name="Departamento de Compras",
        buyer_unit_address="Av. Providencia 1234",
        buyer_unit_commune="Providencia",
        buyer_unit_region="Metropolitana",
        currency_code="CLP",
        estimated_amount=Decimal("150000000"),
        visibility_amount="150000000",
        tipo="Publica",
        codigo_tipo="LR",
        tipo_convocatoria="Abierta",
        days_to_close=10,
        award_date=date(2026, 6, 15),
        estimated_award_date=date(2026, 6, 10),
    )

    source_file_id = uuid4()
    payload = bridge.build_normalized_licitacion_from_snapshot(
        snap, source_file_id=source_file_id
    )

    assert payload is not None
    assert payload["codigo_externo"] == "1274285-76-LR25"
    assert payload["descripcion"] == "Servicios de soporte informatico para sistemas criticos"
    assert payload["comuna_unidad"] == "Providencia"
    assert payload["region_unidad"] == "Metropolitana"
    assert payload["tipo"] == "Publica"
    assert payload["tipo_convocatoria"] == "Abierta"
    assert payload["cantidad_dias_licitacion"] == 10
    assert payload["monto_estimado"] == Decimal("150000000")
    assert payload["visibilidad_monto_raw"] == "150000000"
    assert payload["fecha_publicacion"] is not None
    assert payload["fecha_cierre"] is not None
    assert payload["fecha_adjudicacion"] is not None
    assert payload["fecha_estimada_adjudicacion"] is not None
    assert payload["source_file_id"] == source_file_id
    assert "row_hash_sha256" in payload


def test_api_items_canonicalize_to_normalized_licitacion_items() -> None:
    item_snap = SimpleNamespace(
        external_notice_code="1274285-76-LR25",
        item_correlative=1,
        codigo_producto="43210000",
        codigo_categoria="4321",
        categoria="Equipos informaticos",
        nombre_producto="Servidores de rack 2U",
        descripcion="64 GB RAM, 4 TB SSD",
        unidad_medida="Unidad",
        cantidad="4",
    )

    source_file_id = uuid4()
    payload = bridge.build_normalized_licitacion_item_from_item_snapshot(
        item_snap, source_file_id=source_file_id
    )

    assert payload is not None
    assert payload["codigo_externo"] == "1274285-76-LR25"
    assert payload["codigo_item"] == "1"
    assert payload["correlativo"] == "1"
    assert payload["codigo_producto_onu"] == "43210000"
    assert payload["nombre_producto_generico"] == "Servidores de rack 2U"
    assert payload["descripcion_linea_adquisicion"] == "64 GB RAM, 4 TB SSD"
    assert payload["unidad_medida"] == "Unidad"
    assert payload["cantidad"] == Decimal("4")
    assert payload["source_file_id"] == source_file_id
    assert "row_hash_sha256" in payload


def test_api_items_canonicalize_uses_stable_fallback_key_when_identity_fields_are_missing() -> None:
    item_snap = SimpleNamespace(
        external_notice_code="1274285-76-LR25",
        item_correlative=None,
        codigo_producto=None,
        codigo_categoria=None,
        categoria=None,
        nombre_producto="Servidores de rack 2U",
        descripcion="64 GB RAM, 4 TB SSD",
        unidad_medida="Unidad",
        cantidad="4",
    )

    source_file_id = uuid4()
    first = bridge.build_normalized_licitacion_item_from_item_snapshot(
        item_snap, source_file_id=source_file_id
    )
    second = bridge.build_normalized_licitacion_item_from_item_snapshot(
        item_snap, source_file_id=source_file_id
    )

    assert first is not None
    assert second is not None
    assert first["codigo_item"] == second["codigo_item"]
    assert first["codigo_item"].startswith("item-")
    assert len(first["codigo_item"]) > len("item-")


def test_canonicalize_api_snapshots_orders_item_snapshot_reads_deterministically(monkeypatch) -> None:
    snapshot = SimpleNamespace(
        external_notice_code="1274285-76-LR25",
        notice_id="1274285-76-LR25",
        notice_title="Servicio de soporte TI",
        description="Servicios de soporte informatico para sistemas criticos",
        official_status_code=5,
        official_status_name="Publicada",
        publication_date=date(2026, 5, 8),
        close_date=date(2026, 5, 18),
        buyer_org_code="ORG-001",
        buyer_org_name="Municipalidad X",
        buyer_unit_code="U-10",
        buyer_unit_name="Departamento de Compras",
        buyer_unit_address="Av. Providencia 1234",
        buyer_unit_commune="Providencia",
        buyer_unit_region="Metropolitana",
        currency_code="CLP",
        estimated_amount=Decimal("150000000"),
        visibility_amount="150000000",
        tipo="Publica",
        codigo_tipo="LR",
        tipo_convocatoria="Abierta",
        days_to_close=10,
        award_date=date(2026, 6, 15),
        estimated_award_date=date(2026, 6, 10),
    )
    item_snap = SimpleNamespace(
        external_notice_code="1274285-76-LR25",
        item_correlative=None,
        codigo_producto=None,
        codigo_categoria=None,
        categoria=None,
        nombre_producto="Servidores de rack 2U",
        descripcion="64 GB RAM, 4 TB SSD",
        unidad_medida="Unidad",
        cantidad="4",
        synced_at=datetime(2026, 5, 10, 10, 5, 0),
        observed_at=datetime(2026, 5, 10, 10, 0, 0),
        id=uuid4(),
    )

    session = _QueuedSession(
        [
            _ScalarIterableResult([snapshot]),
            _ScalarIterableResult([item_snap]),
        ]
    )

    monkeypatch.setattr(bridge, "upsert_rows", lambda _session, _model, rows, _conflicts: len(rows))
    monkeypatch.setattr(
        bridge,
        "build_normalized_licitacion_from_snapshot",
        lambda snap, *, source_file_id: {
            "codigo_externo": snap.external_notice_code,
            "source_file_id": source_file_id,
        },
    )

    bridge.canonicalize_api_snapshots_to_normalized(
        session=session,  # type: ignore[arg-type]
        source_file_id=uuid4(),
        pipeline_run_id=uuid4(),
    )

    item_select_sql = str(session.statements[1]).lower()
    assert "order by" in item_select_sql
    assert "synced_at" in item_select_sql
    assert "observed_at" in item_select_sql
    assert "coalesce" in item_select_sql


def test_canonicalize_api_snapshots_prioritizes_detail_source_mode_in_query() -> None:
    session = _QueuedSession([_ScalarIterableResult([])])

    bridge.canonicalize_api_snapshots_to_normalized(
        session=session,  # type: ignore[arg-type]
        source_file_id=uuid4(),
        pipeline_run_id=uuid4(),
    )

    snapshots_select_sql = str(session.statements[0]).lower()
    assert "order by" in snapshots_select_sql
    assert "source_mode" in snapshots_select_sql
    assert "case when" in snapshots_select_sql
    assert "synced_at" in snapshots_select_sql


def test_nulls_do_not_overwrite_existing_non_null_values(
    monkeypatch,
) -> None:
    from backend.pipeline.transform.upsert_engine import _build_complete_only_update_expr
    import sqlalchemy as sa

    mock_stmt = SimpleNamespace()
    mock_stmt.excluded = SimpleNamespace()
    mock_stmt.excluded.description = None

    class _FakeColumn:
        def __init__(self, col_type: sa.types.TypeEngine) -> None:
            self.type = col_type

    mock_model = SimpleNamespace()
    mock_model.description = _FakeColumn(sa.Text())

    expr = _build_complete_only_update_expr(
        model=mock_model, stmt=mock_stmt, field="description"
    )
    compiled = str(expr)
    assert "coalesce" in compiled.lower()

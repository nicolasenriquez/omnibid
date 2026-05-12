from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest

import backend.integrations.mercado_publico.store as store_module
from backend.integrations.mercado_publico.errors import MercadoPublicoRateLimitError
from backend.integrations.mercado_publico.schemas import parse_licitaciones_response
from backend.integrations.mercado_publico.store import (
    PersistedNoticeBatch,
    _comprador_attr,
    _fechas_attr,
    canonical_request_params,
    compute_payload_hash,
    compute_request_hash,
    persist_notice_batch,
    reserve_request_budget,
)


def test_canonical_request_params_removes_ticket() -> None:
    params = {"ticket": "secret", "estado": "activas", "fecha": "08052026"}
    canonical = canonical_request_params(params)
    assert "ticket" not in canonical
    assert canonical == {"estado": "activas", "fecha": "08052026"}


def test_compute_request_hash_ignores_ticket_and_order() -> None:
    first = {"estado": "activas", "fecha": "08052026", "ticket": "one"}
    second = {"ticket": "two", "fecha": "08052026", "estado": "activas"}
    assert compute_request_hash(first) == compute_request_hash(second)


def test_compute_payload_hash_changes_when_payload_changes() -> None:
    base = {"Codigo": 0, "Descripcion": "OK", "Cantidad": 1, "Listado": []}
    changed = {"Codigo": 0, "Descripcion": "OK", "Cantidad": 2, "Listado": []}
    assert compute_payload_hash(base) != compute_payload_hash(changed)


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one(self) -> object:
        return self._value

    def scalar_one_or_none(self) -> object | None:
        return self._value


class _FakeBudgetSession:
    def __init__(self) -> None:
        self.rows: list[object] = []
        self.add_calls = 0

    def in_transaction(self) -> bool:
        return True

    def execute(self, statement: object, params: dict[str, object] | None = None) -> _ScalarResult:
        if params is not None and "lock_token" in params:
            return _ScalarResult(True)
        compiled_params = statement.compile().params  # type: ignore[union-attr]
        request_hash = next(
            (value for key, value in compiled_params.items() if "request_hash" in str(key)),
            None,
        )
        source_system = next(
            (value for key, value in compiled_params.items() if "source_system" in str(key)),
            None,
        )
        request_day = next(
            (value for key, value in compiled_params.items() if "rate_limit_day" in str(key)),
            None,
        )
        for row in self.rows:
            if (
                getattr(row, "request_hash", None) == request_hash
                and getattr(row, "source_system", None) == source_system
                and getattr(row, "rate_limit_day", None) == request_day
            ):
                return _ScalarResult(row)
        return _ScalarResult(None)

    def add(self, row: object) -> None:
        self.add_calls += 1
        self.rows.append(row)

    def flush(self) -> None:
        for row in self.rows:
            if getattr(row, "id", None) is None:
                setattr(row, "id", uuid4())


def _patch_budget_sum(monkeypatch: pytest.MonkeyPatch) -> None:
    def _sum_daily_cost_units(
        session: _FakeBudgetSession,
        *,
        source_system: str,
        request_date: object,
    ) -> int:
        return sum(
            int(getattr(row, "cost_units", 0) or 0)
            for row in session.rows
            if getattr(row, "source_system", None) == source_system
            and getattr(row, "rate_limit_day", None) == request_date
        )

    monkeypatch.setattr(store_module, "_sum_daily_cost_units", _sum_daily_cost_units)


def test_reserve_request_budget_rejects_same_day_over_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_budget_sum(monkeypatch)
    session = _FakeBudgetSession()
    requested_at = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)
    pipeline_run_id = uuid4()

    reserve_request_budget(
        session,  # type: ignore[arg-type]
        pipeline_run_id=pipeline_run_id,
        source_system="mercado_publico",
        endpoint_name="licitaciones.json",
        resource_type="licitacion",
        resource_key="estado=activas",
        request_params={"estado": "activas", "ticket": "secret-one"},
        request_url_safe="https://example.invalid/licitaciones.json?estado=activas&ticket=%2A%2A%2Aredacted%2A%2A%2A",
        daily_limit=1,
        requested_at=requested_at,
    )

    with pytest.raises(MercadoPublicoRateLimitError, match="daily request budget exhausted"):
        reserve_request_budget(
            session,  # type: ignore[arg-type]
            pipeline_run_id=pipeline_run_id,
            source_system="mercado_publico",
            endpoint_name="licitaciones.json",
            resource_type="licitacion",
            resource_key="estado=cerradas",
            request_params={"estado": "cerradas", "ticket": "secret-two"},
            request_url_safe=(
                "https://example.invalid/licitaciones.json?estado=cerradas&ticket=%2A%2A%2Aredacted%2A%2A%2A"
            ),
            daily_limit=1,
            requested_at=requested_at,
        )

    assert session.add_calls == 1


def test_reserve_request_budget_is_idempotent_for_same_day_same_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_budget_sum(monkeypatch)
    session = _FakeBudgetSession()
    requested_at = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)
    pipeline_run_id = uuid4()

    first = reserve_request_budget(
        session,  # type: ignore[arg-type]
        pipeline_run_id=pipeline_run_id,
        source_system="mercado_publico",
        endpoint_name="licitaciones.json",
        resource_type="licitacion",
        resource_key="estado=activas",
        request_params={"estado": "activas", "ticket": "secret-one"},
        request_url_safe="https://example.invalid/licitaciones.json?estado=activas&ticket=%2A%2A%2Aredacted%2A%2A%2A",
        daily_limit=10,
        requested_at=requested_at,
    )
    second = reserve_request_budget(
        session,  # type: ignore[arg-type]
        pipeline_run_id=pipeline_run_id,
        source_system="mercado_publico",
        endpoint_name="licitaciones.json",
        resource_type="licitacion",
        resource_key="estado=activas",
        request_params={"ticket": "secret-two", "estado": "activas"},
        request_url_safe="https://example.invalid/licitaciones.json?estado=activas&ticket=%2A%2A%2Aredacted%2A%2A%2A",
        daily_limit=10,
        requested_at=requested_at,
    )

    assert first.was_existing is False
    assert second.was_existing is True
    assert first.request_id == second.request_id
    assert session.add_calls == 1


def test_reserve_request_budget_persists_safe_url_without_ticket_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_budget_sum(monkeypatch)
    session = _FakeBudgetSession()
    requested_at = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)
    safe_url = "https://example.invalid/licitaciones.json?estado=activas&ticket=%2A%2A%2Aredacted%2A%2A%2A"

    reserve_request_budget(
        session,  # type: ignore[arg-type]
        pipeline_run_id=uuid4(),
        source_system="mercado_publico",
        endpoint_name="licitaciones.json",
        resource_type="licitacion",
        resource_key="estado=activas",
        request_params={"estado": "activas", "ticket": "secret-ticket-value"},
        request_url_safe=safe_url,
        daily_limit=10,
        requested_at=requested_at,
        request_metadata={"trigger": "unit-test"},
    )

    saved = session.rows[0]
    assert getattr(saved, "request_url_safe", None) == safe_url
    assert "secret-ticket-value" not in str(getattr(saved, "request_url_safe", ""))
    assert getattr(saved, "request_metadata", None) == {"trigger": "unit-test"}


class _RecordingPersistenceSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.snapshot_inserts: list[dict[str, object]] = []
        self.snapshot_updates: list[dict[str, object]] = []
        self.item_inserts: list[dict[str, object]] = []
        self.item_updates: list[dict[str, object]] = []

    def in_transaction(self) -> bool:
        return True

    def execute(self, statement: object, params: dict[str, object] | None = None) -> _ScalarResult:
        _ = params
        stmt_str = str(statement)
        if "mercado_publico_notice_item_snapshot" in stmt_str:
            if "INSERT" in stmt_str:
                compiled = statement.compile()  # type: ignore[union-attr]
                self.item_inserts.append(dict(compiled.params))
                return _ScalarResult(1)
            if "UPDATE" in stmt_str:
                compiled = statement.compile()  # type: ignore[union-attr]
                self.item_updates.append(dict(compiled.params))
                return _ScalarResult(1)
            return _ScalarResult(None)
        if "mercado_publico_notice_snapshot" in stmt_str:
            if "INSERT" in stmt_str:
                compiled = statement.compile()  # type: ignore[union-attr]
                self.snapshot_inserts.append(dict(compiled.params))
                return _ScalarResult(1)
            if "UPDATE" in stmt_str:
                compiled = statement.compile()  # type: ignore[union-attr]
                self.snapshot_updates.append(dict(compiled.params))
                return _ScalarResult(1)
            return _ScalarResult(None)
        return _ScalarResult(None)

    def add(self, row: object) -> None:
        self.added.append(row)
        if getattr(row, "id", None) is None:
            setattr(row, "id", uuid4())

    def flush(self) -> None:
        pass

    def begin(self) -> "_NoOpContext":
        return _NoOpContext()


class _NoOpContext:
    def __enter__(self) -> "_NoOpContext":
        return self

    def __exit__(self, *args: object) -> None:
        pass


def _detail_notices() -> list[object]:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "detail_by_codigo_payload.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    response = parse_licitaciones_response(payload)
    return response.notices


def _summary_notices() -> list[object]:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "summary_payload.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    response = parse_licitaciones_response(payload)
    return response.notices


def test_persist_detail_notice_populates_enriched_fields() -> None:
    notices = _detail_notices()
    notice = notices[0]
    session = _RecordingPersistenceSession()

    result = persist_notice_batch(
        session,  # type: ignore[arg-type]
        pipeline_run_id=uuid4(),
        endpoint_name="licitaciones.json",
        resource_type="licitacion",
        resource_key="codigo=1274285-76-LR25",
        request_params={"codigo": "1274285-76-LR25", "ticket": "test"},
        payload={"Codigo": 0, "Listado": []},
        notices=notices,
        source_mode="detail-by-codigo",
    )

    assert result.snapshots_upserted == 1
    snap = session.snapshot_inserts[0]
    assert snap["description"] == notice.description
    assert snap["buyer_unit_region"] == "Metropolitana"
    assert snap["buyer_unit_commune"] == "Providencia"
    assert snap["buyer_unit_address"] == "Av. Providencia 1234"
    assert snap["tipo"] == "Publica"
    assert snap["api_completeness_level"] == "detail"
    assert snap["claim_count"] == 3
    assert snap["funding_source"] == "Municipal"
    assert snap["days_to_close"] == 15
    assert snap["codigo_tipo"] == "LR"


def test_persist_detail_notice_persists_items() -> None:
    notices = _detail_notices()
    session = _RecordingPersistenceSession()

    result = persist_notice_batch(
        session,  # type: ignore[arg-type]
        pipeline_run_id=uuid4(),
        endpoint_name="licitaciones.json",
        resource_type="licitacion",
        resource_key="codigo=1274285-76-LR25",
        request_params={"codigo": "1274285-76-LR25", "ticket": "test"},
        payload={"Codigo": 0, "Listado": []},
        notices=notices,
        source_mode="detail-by-codigo",
    )

    assert result.items_seen == 2
    assert result.items_persisted == 2
    assert len(session.item_inserts) == 2
    first_item = session.item_inserts[0]
    assert first_item["codigo_producto"] == "43210000"
    assert first_item["nombre_producto"] == "Servidores de rack para centro de datos"
    assert first_item["cantidad"] == "4"
    assert first_item["unidad_medida"] == "Unidad"
    assert first_item["item_correlative"] == 1
    second_item = session.item_inserts[1]
    assert second_item["item_correlative"] == 2
    assert second_item["codigo_producto"] == "81110000"


def test_persist_summary_notice_leaves_enriched_fields_null() -> None:
    notices = _summary_notices()
    session = _RecordingPersistenceSession()

    result = persist_notice_batch(
        session,  # type: ignore[arg-type]
        pipeline_run_id=uuid4(),
        endpoint_name="licitaciones.json",
        resource_type="licitacion",
        resource_key="estado=activas",
        request_params={"estado": "activas", "ticket": "test"},
        payload={"Codigo": 0, "Listado": []},
        notices=notices,
        source_mode="active-discovery",
    )

    assert result.snapshots_upserted == 2
    for snap in session.snapshot_inserts:
        assert snap["description"] is None
        assert snap["buyer_unit_region"] is None
        assert snap["buyer_unit_commune"] is None
        assert snap["buyer_unit_address"] is None
        assert snap["api_completeness_level"] == "summary"
        assert snap["tipo"] is None
        assert snap["claim_count"] is None
    assert result.items_seen == 0
    assert result.items_persisted == 0
    assert len(session.item_inserts) == 0


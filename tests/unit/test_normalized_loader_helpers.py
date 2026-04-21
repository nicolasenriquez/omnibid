from __future__ import annotations

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import dialect as pg_dialect

from backend.models.normalized import NormalizedOferta
from backend.models.normalized import NormalizedOrdenCompra
from backend.normalized.transform import build_oferta_payload
from backend.normalized.transform import build_orden_compra_payload

ROOT = Path(__file__).resolve().parents[2]
BUILD_NORMALIZED_PATH = ROOT / "scripts" / "build_normalized.py"
SPEC = importlib.util.spec_from_file_location("build_normalized_script", BUILD_NORMALIZED_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load build_normalized module from {BUILD_NORMALIZED_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
dedupe_rows = MODULE.dedupe_rows
upsert_rows = MODULE.upsert_rows
calculate_max_rows_per_upsert = MODULE.calculate_max_rows_per_upsert
resolve_start_after_id = MODULE.resolve_start_after_id


class _DummyResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _DummySession:
    def __init__(self) -> None:
        self.execute_calls = 0

    def execute(self, _stmt: object) -> _DummyResult:
        self.execute_calls += 1
        return _DummyResult(1)


class _ThresholdSession:
    def __init__(self, max_params: int) -> None:
        self.max_params = max_params
        self.execute_calls = 0

    def execute(self, stmt: object) -> _DummyResult:
        self.execute_calls += 1
        params_count = len(stmt.compile(dialect=pg_dialect()).params)
        if params_count > self.max_params:
            raise sa.exc.OperationalError("too many bind params", params=None, orig=Exception("bind limit"))
        return _DummyResult(1)


def test_dedupe_rows_keeps_latest_payload_for_same_business_key() -> None:
    rows = [
        {"codigo_externo": "L-1", "nombre": "old"},
        {"codigo_externo": "L-1", "nombre": "new"},
        {"codigo_externo": "L-2", "nombre": "only"},
    ]

    deduped = dedupe_rows(rows, ["codigo_externo"])

    by_key = {row["codigo_externo"]: row for row in deduped}
    assert len(deduped) == 2
    assert by_key["L-1"]["nombre"] == "new"
    assert by_key["L-2"]["nombre"] == "only"


def test_dedupe_rows_fails_when_business_key_is_missing() -> None:
    rows = [
        {"codigo_externo": "L-1", "nombre": "ok"},
        {"nombre": "missing-key"},
    ]

    with pytest.raises(ValueError, match="missing business key"):
        dedupe_rows(rows, ["codigo_externo"])


def test_dedupe_rows_fails_when_business_key_fields_are_empty() -> None:
    rows = [{"codigo_externo": "L-1"}]

    with pytest.raises(ValueError, match="conflict key fields"):
        dedupe_rows(rows, [])


def test_calculate_max_rows_per_upsert_produces_safe_limit() -> None:
    # 65 columns is the NormalizedOrdenCompra payload width.
    limit = calculate_max_rows_per_upsert(65)
    assert limit == 503


def test_upsert_rows_splits_batches_when_param_limit_would_be_exceeded() -> None:
    raw = {"Codigo": "OC-BASE"}
    base_payload = build_orden_compra_payload(raw, source_file_id=uuid4(), row_hash_sha256="h" * 64)
    assert base_payload is not None

    max_rows = calculate_max_rows_per_upsert(len(base_payload))
    rows: list[dict[str, object]] = []
    for idx in range(max_rows + 5):
        row = dict(base_payload)
        row["codigo_oc"] = f"OC-{idx}"
        rows.append(row)

    dummy = _DummySession()
    upserted = upsert_rows(dummy, NormalizedOrdenCompra, rows, ["codigo_oc"])

    assert dummy.execute_calls == 2
    assert upserted == 2


def test_upsert_rows_retries_with_smaller_batches_on_operational_error() -> None:
    base_payload = build_oferta_payload(
        {
            "CodigoExterno": "L-BASE",
            "CodigoProveedor": "P-1",
            "NombreProveedor": "Proveedor",
        },
        source_file_id=uuid4(),
        row_hash_sha256="h" * 64,
    )
    assert base_payload is not None

    rows: list[dict[str, object]] = []
    for idx in range(600):
        row = dict(base_payload)
        row["oferta_key_sha256"] = f"h{idx:063d}"
        rows.append(row)

    # First 600-row statement exceeds this synthetic limit and must be split/retried.
    session = _ThresholdSession(max_params=10_000)
    upserted = upsert_rows(session, NormalizedOferta, rows, ["oferta_key_sha256"])

    assert upserted > 0
    assert session.execute_calls >= 3


def test_resolve_start_after_id_uses_checkpoint_when_incremental() -> None:
    dataset_state = {"last_processed_raw_id": "12345"}
    assert resolve_start_after_id(dataset_state, incremental=True) == 12345


def test_resolve_start_after_id_returns_zero_when_checkpoint_missing() -> None:
    dataset_state = {"last_raw_id": 777}
    assert resolve_start_after_id(dataset_state, incremental=True) == 0


def test_resolve_start_after_id_returns_zero_when_incremental_disabled() -> None:
    dataset_state = {"last_processed_raw_id": 999}
    assert resolve_start_after_id(dataset_state, incremental=False) == 0

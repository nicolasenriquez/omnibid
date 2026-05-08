from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.normalized import mp_api_notice_refresh


def _snapshot(
    *,
    code: str = "100-1-LR26",
    publication_date: date | None = date(2026, 5, 8),
    close_date: date | None = date(2026, 5, 10),
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        pipeline_run_id=uuid4(),
        request_id=uuid4(),
        payload_id=uuid4(),
        endpoint_name="licitaciones.json",
        resource_key="fecha=08052026",
        notice_id=code,
        external_notice_code=code,
        notice_title=f"Licitacion {code}",
        official_status_code=5,
        official_status_name="Publicada",
        publication_date=publication_date,
        close_date=close_date,
        buyer_org_code="7010",
        buyer_org_name="Municipalidad",
        buyer_unit_code="U-10",
        buyer_unit_name="Unidad Compras",
        currency_code="CLP",
        estimated_amount=123456.78,
        snapshot_date=publication_date or date(2026, 5, 8),
        synced_at=datetime(2026, 5, 8, 10, 0, 0),
    )


def test_build_silver_notice_payload_from_snapshot_maps_supported_fields_and_defaults() -> None:
    source_file_id = uuid4()
    payload = mp_api_notice_refresh.build_silver_notice_payload_from_snapshot(
        _snapshot(),
        source_file_id=source_file_id,
    )
    assert payload is not None
    assert payload["notice_id"] == "100-1-LR26"
    assert payload["external_notice_code"] == "100-1-LR26"
    assert payload["notice_title"] == "Licitacion 100-1-LR26"
    assert payload["notice_status_code"] == "5"
    assert payload["notice_status_name"] == "Publicada"
    assert payload["publication_date"] == datetime(2026, 5, 8, 0, 0, 0)
    assert payload["close_date"] == datetime(2026, 5, 10, 0, 0, 0)
    assert payload["days_publication_to_close"] == 2
    assert payload["source_file_id"] == source_file_id
    assert payload["row_hash_sha256"] and len(payload["row_hash_sha256"]) == 64

    # Unsupported fields stay explicit and non-synthesized.
    assert payload["notice_description_raw"] is None
    assert payload["notice_description_clean"] is None
    assert payload["notice_line_count"] is None
    assert payload["notice_bid_count"] is None
    assert payload["notice_supplier_count"] is None
    assert payload["notice_purchase_order_count"] is None
    assert payload["is_public_tender_flag"] is False
    assert payload["is_private_tender_flag"] is False
    assert payload["notice_has_purchase_order_flag"] is False


def test_build_silver_notice_payload_from_snapshot_row_hash_is_stable() -> None:
    source_file_id = uuid4()
    snapshot = _snapshot()

    first = mp_api_notice_refresh.build_silver_notice_payload_from_snapshot(
        snapshot,
        source_file_id=source_file_id,
    )
    second = mp_api_notice_refresh.build_silver_notice_payload_from_snapshot(
        snapshot,
        source_file_id=source_file_id,
    )
    assert first is not None
    assert second is not None
    assert first["row_hash_sha256"] == second["row_hash_sha256"]


def test_refresh_uses_notice_id_upsert_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    sample_snapshot = _snapshot()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        mp_api_notice_refresh,
        "select_latest_notice_snapshots",
        lambda *_args, **_kwargs: [sample_snapshot],
    )

    def _fake_upsert_rows(_session, _model, rows, conflict_fields):
        captured["rows"] = rows
        captured["conflict_fields"] = conflict_fields
        return len(rows)

    monkeypatch.setattr(mp_api_notice_refresh, "upsert_rows", _fake_upsert_rows)

    summary = mp_api_notice_refresh.refresh_silver_notice_from_mp_api_snapshots(
        session=object(),  # type: ignore[arg-type]
        source_file_id=uuid4(),
        window_dates=[date(2026, 5, 8)],
    )

    assert summary.notice_candidates == 1
    assert summary.upserted_notices == 1
    assert captured["conflict_fields"] == ["notice_id"]

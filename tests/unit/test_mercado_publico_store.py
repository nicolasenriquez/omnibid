from __future__ import annotations

from backend.integrations.mercado_publico.store import (
    canonical_request_params,
    compute_payload_hash,
    compute_request_hash,
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


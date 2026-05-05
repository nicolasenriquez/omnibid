from __future__ import annotations

from typing import Any, cast

from backend.api import dataset_summary


class _DummyResult:
    def __init__(self, scalar: int) -> None:
        self._scalar = scalar

    def scalar_one(self) -> int:
        return self._scalar


class _DummySession:
    def __init__(self, scalars: list[int]) -> None:
        self._scalars = scalars
        self.execute_calls = 0

    def execute(self, _stmt: object) -> _DummyResult:
        if not self._scalars:
            raise AssertionError("no dummy scalar configured for execute")
        self.execute_calls += 1
        return _DummyResult(self._scalars.pop(0))


def test_compute_dataset_summary_counts_uses_shared_model_contract() -> None:
    session = _DummySession([10, 20, 30, 40, 50, 60, 70, 80])

    payload = dataset_summary.compute_dataset_summary_counts(cast(Any, session))

    assert payload == {
        "source_files_count": 10,
        "raw_licitaciones_count": 20,
        "raw_ordenes_compra_count": 30,
        "normalized_licitaciones_count": 40,
        "normalized_licitacion_items_count": 50,
        "normalized_ofertas_count": 60,
        "normalized_ordenes_compra_count": 70,
        "normalized_ordenes_compra_items_count": 80,
    }
    assert session.execute_calls == 8

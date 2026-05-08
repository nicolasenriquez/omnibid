from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.integrations.mercado_publico.errors import (
    MercadoPublicoContractDriftError,
    MercadoPublicoRequestError,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "fetch_mp_api.py"
MODULE_NAME = "fetch_mp_api_script_module"

_SPEC = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
fetch_mp_api = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fetch_mp_api)


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def test_execute_with_tracking_marks_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()
    run = SimpleNamespace(id=uuid4())
    step = SimpleNamespace()
    captured: dict[str, object] = {}

    monkeypatch.setattr(fetch_mp_api, "create_sync_run", lambda *args, **kwargs: (run, step))
    monkeypatch.setattr(
        fetch_mp_api,
        "execute_sync_mode",
        lambda **kwargs: SimpleNamespace(
            mode="active-discovery",
            requests=1,
            notices_seen=2,
            notices_skipped_missing_external_notice_code=0,
            snapshots_upserted=2,
            snapshots_inserted=2,
            snapshots_updated=0,
        ),
    )
    monkeypatch.setattr(
        fetch_mp_api,
        "mark_sync_run_completed",
        lambda **kwargs: captured.update({"completed": kwargs}),
    )
    monkeypatch.setattr(
        fetch_mp_api,
        "mark_sync_run_failed",
        lambda **kwargs: captured.update({"failed": kwargs}),
    )

    result = fetch_mp_api._execute_with_tracking(  # noqa: SLF001
        session,  # type: ignore[arg-type]
        client=object(),  # type: ignore[arg-type]
        mode="active-discovery",
        target_date=date(2026, 5, 8),
        window_days=4,
        estado=None,
        codigos=[],
    )

    assert result == 0
    assert session.commits == 1
    assert session.rollbacks == 0
    assert "completed" in captured
    assert "failed" not in captured


@pytest.mark.parametrize(
    "exc",
    [
        MercadoPublicoRequestError("retry exhausted"),
        MercadoPublicoContractDriftError("contract drift"),
    ],
)
def test_execute_with_tracking_marks_failed_on_errors(
    monkeypatch: pytest.MonkeyPatch,
    exc: Exception,
) -> None:
    session = _FakeSession()
    run = SimpleNamespace(id=uuid4())
    step = SimpleNamespace()
    captured: dict[str, object] = {}

    monkeypatch.setattr(fetch_mp_api, "create_sync_run", lambda *args, **kwargs: (run, step))

    def _raise(**kwargs):
        _ = kwargs
        raise exc

    monkeypatch.setattr(fetch_mp_api, "execute_sync_mode", _raise)
    monkeypatch.setattr(
        fetch_mp_api,
        "mark_sync_run_completed",
        lambda **kwargs: captured.update({"completed": kwargs}),
    )
    monkeypatch.setattr(
        fetch_mp_api,
        "mark_sync_run_failed",
        lambda **kwargs: captured.update({"failed": kwargs}),
    )

    result = fetch_mp_api._execute_with_tracking(  # noqa: SLF001
        session,  # type: ignore[arg-type]
        client=object(),  # type: ignore[arg-type]
        mode="active-discovery",
        target_date=None,
        window_days=4,
        estado=None,
        codigos=[],
    )

    assert result == 1
    assert session.rollbacks == 1
    assert session.commits == 1
    assert "failed" in captured
    assert "completed" not in captured

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]

INGEST_RAW_PATH = ROOT / "scripts" / "ingest_raw.py"
INGEST_SPEC = importlib.util.spec_from_file_location("ingest_raw_script", INGEST_RAW_PATH)
if INGEST_SPEC is None or INGEST_SPEC.loader is None:
    raise RuntimeError(f"Unable to load ingest_raw module from {INGEST_RAW_PATH}")
INGEST_MODULE = importlib.util.module_from_spec(INGEST_SPEC)
INGEST_SPEC.loader.exec_module(INGEST_MODULE)

BUILD_NORMALIZED_PATH = ROOT / "scripts" / "build_normalized.py"
BUILD_SPEC = importlib.util.spec_from_file_location("build_normalized_script", BUILD_NORMALIZED_PATH)
if BUILD_SPEC is None or BUILD_SPEC.loader is None:
    raise RuntimeError(f"Unable to load build_normalized module from {BUILD_NORMALIZED_PATH}")
BUILD_MODULE = importlib.util.module_from_spec(BUILD_SPEC)
BUILD_SPEC.loader.exec_module(BUILD_MODULE)


class _DummySession:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def rollback(self) -> None:
        self.calls.append("rollback")

    def commit(self) -> None:
        self.calls.append("commit")


def test_persist_raw_ingest_failure_rolls_back_before_commit() -> None:
    calls: list[str] = []
    session = _DummySession(calls)
    batch = SimpleNamespace(status="started", finished_at=None)
    step = SimpleNamespace(status="running", finished_at=None, error_details={})
    run = SimpleNamespace(status="running", finished_at=None, error_summary=None)

    INGEST_MODULE.persist_raw_ingest_failure(
        session=session,
        batch=batch,
        step=step,
        run=run,
        exc=RuntimeError("boom"),
    )

    assert calls == ["rollback", "commit"]
    assert batch.status == "failed"
    assert step.status == "failed"
    assert run.status == "failed"
    assert step.error_details == {"error": "boom"}
    assert run.error_summary == "boom"


def test_persist_failed_dataset_state_rolls_back_before_save(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[str] = []
    session = _DummySession(calls)
    state = {"licitacion": {"status": "running"}}
    snapshot = {"total_rows": 123, "max_id": 456}
    state_path = tmp_path / "state.json"

    def fake_save_state(path: Path, _state: dict[str, Any]) -> None:
        calls.append("save_state")
        assert path == state_path

    monkeypatch.setattr(BUILD_MODULE, "save_state", fake_save_state)

    BUILD_MODULE.persist_failed_dataset_state(
        session=session,
        state=state,
        dataset="licitacion",
        snapshot=snapshot,
        state_path=state_path,
    )

    assert calls == ["rollback", "save_state"]
    assert state["licitacion"]["status"] == "failed"
    assert state["licitacion"]["source_total_rows"] == 123
    assert state["licitacion"]["source_max_id"] == 456


def test_build_normalized_run_init_failure_persists_failed_dataset_state(
    monkeypatch: Any, tmp_path: Path
) -> None:
    class _Session:
        def __init__(self) -> None:
            self.rollback_calls = 0
            self.commit_calls = 0

        def rollback(self) -> None:
            self.rollback_calls += 1

        def commit(self) -> None:
            self.commit_calls += 1

    class _SessionContext:
        def __init__(self) -> None:
            self.session = _Session()

        def __enter__(self) -> _Session:
            return self.session

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    saved_states: list[dict[str, Any]] = []
    context = _SessionContext()

    def fake_load_state(_: Path) -> dict[str, Any]:
        return {}

    def fake_save_state(_: Path, state: dict[str, Any]) -> None:
        saved_states.append({k: dict(v) if isinstance(v, dict) else v for k, v in state.items()})

    monkeypatch.setattr(BUILD_MODULE, "SessionLocal", lambda: context)
    monkeypatch.setattr(BUILD_MODULE, "load_state", fake_load_state)
    monkeypatch.setattr(BUILD_MODULE, "save_state", fake_save_state)
    monkeypatch.setattr(BUILD_MODULE, "raw_snapshot", lambda _session, _dataset: {"total_rows": 10, "max_id": 10})
    monkeypatch.setattr(BUILD_MODULE, "should_skip_dataset", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        BUILD_MODULE,
        "create_normalized_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("run init failed")),
    )
    mark_failed_calls: list[str] = []
    monkeypatch.setattr(
        BUILD_MODULE,
        "mark_normalized_run_failed",
        lambda *_args, **_kwargs: mark_failed_calls.append("called"),
    )
    monkeypatch.setattr(
        BUILD_MODULE.sys,
        "argv",
        [
            "build_normalized.py",
            "--dataset",
            "licitacion",
            "--state-path",
            str(tmp_path / "normalized_state.json"),
            "--no-progress",
        ],
    )

    with pytest.raises(RuntimeError, match="run init failed"):
        BUILD_MODULE.main()

    assert mark_failed_calls == []
    assert context.session.rollback_calls == 1
    assert len(saved_states) >= 2
    assert saved_states[0]["licitacion"]["status"] == "running"
    assert saved_states[-1]["licitacion"]["status"] == "failed"
    assert saved_states[-1]["licitacion"]["source_total_rows"] == 10
    assert saved_states[-1]["licitacion"]["source_max_id"] == 10

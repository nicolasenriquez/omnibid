from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
BUILD_NORMALIZED_PATH = ROOT / "scripts" / "build_normalized.py"
SPEC = importlib.util.spec_from_file_location("build_normalized_script", BUILD_NORMALIZED_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load build_normalized module from {BUILD_NORMALIZED_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

collect_normalized_quality_issues = MODULE.collect_normalized_quality_issues
evaluate_normalized_quality_gate = MODULE.evaluate_normalized_quality_gate
persist_normalized_quality_issues = MODULE.persist_normalized_quality_issues
mark_normalized_run_completed = MODULE.mark_normalized_run_completed
mark_normalized_run_failed = MODULE.mark_normalized_run_failed
QUALITY_GATE_ISSUE_TYPE_REJECTED_ROWS = MODULE.QUALITY_GATE_ISSUE_TYPE_REJECTED_ROWS
QUALITY_GATE_SEVERITY_ERROR = MODULE.QUALITY_GATE_SEVERITY_ERROR


class _DummySession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.flush_calls = 0

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flush_calls += 1


def test_persist_normalized_quality_issues_saves_issue_context() -> None:
    entity_metrics = {
        "licitaciones": {
            "processed_rows": 1_000,
            "rejected_rows": 2,
        }
    }
    issues = collect_normalized_quality_issues(entity_metrics)
    assert len(issues) == 1
    issue = issues[0]
    assert issue["issue_type"] == QUALITY_GATE_ISSUE_TYPE_REJECTED_ROWS
    assert issue["severity"] == "warning"

    session = _DummySession()
    run_id = uuid4()

    persist_normalized_quality_issues(
        session=session,
        run_id=run_id,
        dataset="licitacion",
        issues=issues,
    )

    assert session.flush_calls == 1
    assert len(session.added) == 1
    added_issue = session.added[0]
    assert added_issue.run_id == run_id
    assert added_issue.dataset_type == "licitacion"
    assert added_issue.table_name == "normalized_licitaciones"
    assert added_issue.issue_type == QUALITY_GATE_ISSUE_TYPE_REJECTED_ROWS
    assert added_issue.severity == "warning"
    assert added_issue.record_ref == "licitaciones"
    assert added_issue.details["rejected_rows"] == 2


def test_quality_gate_fails_when_dataset_error_rate_exceeds_threshold() -> None:
    entity_metrics = {
        "licitaciones": {
            "processed_rows": 1_000,
            "rejected_rows": 6,
        }
    }
    issues = collect_normalized_quality_issues(entity_metrics)

    decision = evaluate_normalized_quality_gate(entity_metrics, issues)

    assert decision["decision"] == "failed"
    assert decision["decision_reason"] == "dataset_error_rate_exceeded_threshold"
    assert decision["dataset_metrics"]["error_rate"] > 0.005


def test_quality_gate_fails_when_critical_error_issue_exists() -> None:
    entity_metrics = {
        "licitaciones": {
            "processed_rows": 1_000,
            "rejected_rows": 1,
        }
    }
    issues = [
        {
            "issue_type": QUALITY_GATE_ISSUE_TYPE_REJECTED_ROWS,
            "severity": QUALITY_GATE_SEVERITY_ERROR,
            "details": {"processed_rows": 1_000, "rejected_rows": 1, "error_rate": 0.001},
        }
    ]

    decision = evaluate_normalized_quality_gate(entity_metrics, issues)

    assert decision["decision"] == "failed"
    assert decision["decision_reason"] == "critical_error_issue_exists"


def test_quality_gate_warns_when_issues_exist_below_failure_threshold() -> None:
    entity_metrics = {
        "licitaciones": {
            "processed_rows": 1_000,
            "rejected_rows": 1,
        }
    }
    issues = collect_normalized_quality_issues(entity_metrics)

    decision = evaluate_normalized_quality_gate(entity_metrics, issues)

    assert decision["decision"] == "warning"
    assert decision["decision_reason"] == "warning_issues_below_threshold"


def test_run_metadata_persists_quality_gate_policy_and_reason() -> None:
    run = SimpleNamespace(
        config={"mode": "incremental"},
        status="running",
        finished_at=None,
        error_summary=None,
    )
    step = SimpleNamespace(
        status="running",
        finished_at=None,
        rows_in=None,
        rows_rejected=None,
        error_details={},
    )
    quality_gate = {
        "policy_version": "quality_gate_policy_v1",
        "thresholds": {
            "max_error_rate": 0.005,
            "fail_on_critical_error": True,
            "critical_issue_types": [QUALITY_GATE_ISSUE_TYPE_REJECTED_ROWS],
        },
        "issue_counts": {"total": 1, "error": 0, "warning": 1},
        "dataset_metrics": {"processed_rows": 100, "rejected_rows": 1, "error_rate": 0.01},
        "decision": "warning",
        "decision_reason": "warning_issues_below_threshold",
    }

    mark_normalized_run_completed(
        run=run,
        step=step,
        processed_rows=100,
        quality_gate=quality_gate,
    )

    assert run.status == "completed"
    assert run.config["quality_gate"]["policy_version"] == "quality_gate_policy_v1"
    assert run.config["quality_gate"]["thresholds"]["max_error_rate"] == 0.005
    assert run.config["quality_gate"]["decision_reason"] == "warning_issues_below_threshold"
    assert step.rows_in == 100
    assert step.rows_rejected == 1


def test_failed_run_persists_quality_gate_context() -> None:
    run = SimpleNamespace(config={}, status="running", finished_at=None, error_summary=None)
    step = SimpleNamespace(status="running", finished_at=None, error_details={})
    quality_gate = {
        "policy_version": "quality_gate_policy_v1",
        "decision": "failed",
        "decision_reason": "dataset_error_rate_exceeded_threshold",
    }

    mark_normalized_run_failed(
        run=run,
        step=step,
        error_summary="normalized quality gate failed",
        quality_gate=quality_gate,
    )

    assert run.status == "failed"
    assert run.error_summary == "normalized quality gate failed"
    assert run.config["quality_gate"]["decision"] == "failed"
    assert step.status == "failed"
    assert step.error_details["quality_gate"]["decision_reason"] == "dataset_error_rate_exceeded_threshold"


def test_quality_gate_failure_keeps_previous_incremental_checkpoint(
    monkeypatch: Any, tmp_path: Path
) -> None:
    class _DummySession:
        def commit(self) -> None:
            return None

        def rollback(self) -> None:
            return None

    class _SessionContext:
        def __enter__(self) -> _DummySession:
            return _DummySession()

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    initial_state = {
        "licitacion": {
            "status": "completed",
            "last_processed_raw_id": 100,
            "processed_rows_total": 25,
        }
    }
    saved_states: list[dict[str, Any]] = []

    def fake_load_state(_: Path) -> dict[str, Any]:
        return copy.deepcopy(initial_state)

    def fake_save_state(_: Path, state: dict[str, Any]) -> None:
        saved_states.append(copy.deepcopy(state))

    def fake_process_licitaciones(**_: Any) -> dict[str, Any]:
        return {
            "processed_rows": 50,
            "last_raw_id": 150,
            "entity_metrics": {"licitaciones": {"processed_rows": 50, "rejected_rows": 50}},
        }

    monkeypatch.setattr(MODULE, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(MODULE, "load_state", fake_load_state)
    monkeypatch.setattr(MODULE, "save_state", fake_save_state)
    monkeypatch.setattr(MODULE, "raw_snapshot", lambda _session, _dataset: {"total_rows": 150, "max_id": 150})
    monkeypatch.setattr(MODULE, "should_skip_dataset", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        MODULE,
        "create_normalized_run",
        lambda _session, _dataset, _mode: (SimpleNamespace(id=uuid4()), SimpleNamespace()),
    )
    monkeypatch.setattr(MODULE, "process_licitaciones", fake_process_licitaciones)
    monkeypatch.setattr(MODULE, "collect_normalized_quality_issues", lambda _metrics: [])
    monkeypatch.setattr(MODULE, "persist_normalized_quality_issues", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        MODULE,
        "evaluate_normalized_quality_gate",
        lambda _metrics, _issues: {"decision": "failed", "decision_reason": "forced_failure"},
    )
    monkeypatch.setattr(MODULE, "mark_normalized_run_failed", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        MODULE.sys,
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

    exit_code = MODULE.main()

    assert exit_code == 1
    assert saved_states
    final_dataset_state = saved_states[-1]["licitacion"]
    assert final_dataset_state["status"] == "failed"
    assert final_dataset_state["start_after_id"] == 100
    assert final_dataset_state["last_processed_raw_id"] == 100
    assert final_dataset_state["last_raw_id"] == 150

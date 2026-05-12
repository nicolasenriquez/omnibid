from __future__ import annotations

from datetime import UTC, date, datetime
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.pipeline.extract.mp_api_errors import (
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

DAILY_SCRIPT_PATH = REPO_ROOT / "scripts" / "run_mp_api_daily_pipeline.py"
DAILY_MODULE_NAME = "run_mp_api_daily_pipeline_script_module"

_DAILY_SPEC = importlib.util.spec_from_file_location(DAILY_MODULE_NAME, DAILY_SCRIPT_PATH)
if _DAILY_SPEC is None or _DAILY_SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {DAILY_SCRIPT_PATH}")
run_mp_api_daily_pipeline = importlib.util.module_from_spec(_DAILY_SPEC)
_DAILY_SPEC.loader.exec_module(run_mp_api_daily_pipeline)


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


def test_validate_production_database_safety_rejects_default_postgres_credentials() -> None:
    with pytest.raises(ValueError, match="rejects default postgres credentials"):
        fetch_mp_api._validate_production_database_safety(  # noqa: SLF001
            app_env="production",
            database_url="postgresql+psycopg://postgres:postgres@db:5432/chilecompra",
        )


def test_validate_production_database_safety_rejects_localhost_in_production() -> None:
    with pytest.raises(ValueError, match="requires a non-local DATABASE_URL host"):
        fetch_mp_api._validate_production_database_safety(  # noqa: SLF001
            app_env="prod",
            database_url="postgresql+psycopg://app_user:strong@localhost:5432/chilecompra",
        )


def test_main_dry_run_does_not_open_db_session(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = SimpleNamespace(
        mode="active-discovery",
        target_date=None,
        start_date=None,
        end_date=None,
        window_days=4,
        estado=None,
        codigo=[],
        dry_run=True,
        max_requests=25,
        requested_by="unit_test",
    )
    parser = SimpleNamespace(parse_args=lambda: args)
    settings = SimpleNamespace(enabled=False, normalized_base_url="https://example.invalid")

    monkeypatch.setattr(fetch_mp_api, "_parser", lambda: parser)
    monkeypatch.setattr(fetch_mp_api, "_build_client_settings", lambda: settings)
    monkeypatch.setattr(fetch_mp_api, "_validate_runtime_mode", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        fetch_mp_api,
        "SessionLocal",
        lambda: (_ for _ in ()).throw(AssertionError("SessionLocal should not be used in dry-run")),
    )
    monkeypatch.setattr(
        fetch_mp_api,
        "_execute_with_tracking",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("_execute_with_tracking should not run in dry-run")
        ),
    )

    exit_code = fetch_mp_api.main()

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "dry-run ok" in output


def test_daily_pipeline_dry_run_does_not_open_db_session(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = SimpleNamespace(
        target_date=date(2026, 5, 10),
        window_days=4,
        estado=None,
        refresh_only=False,
        dry_run=True,
        requested_by="unit_test",
        max_requests=3,
    )
    parser = SimpleNamespace(parse_args=lambda: args)
    app_settings = SimpleNamespace(
        app_env="local",
        database_url="postgresql+psycopg://app:pw@localhost:5432/chilecompra",
    )
    mp_settings = SimpleNamespace(enabled=False, normalized_base_url="https://example.invalid")

    monkeypatch.setattr(run_mp_api_daily_pipeline, "_parser", lambda: parser)
    monkeypatch.setattr(run_mp_api_daily_pipeline, "get_settings", lambda: app_settings)
    monkeypatch.setattr(run_mp_api_daily_pipeline, "from_app_settings", lambda _settings: mp_settings)
    monkeypatch.setattr(
        run_mp_api_daily_pipeline,
        "SessionLocal",
        lambda: (_ for _ in ()).throw(AssertionError("SessionLocal should not be used in dry-run")),
    )
    monkeypatch.setattr(
        run_mp_api_daily_pipeline,
        "run_mp_api_daily_notice_pipeline",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("pipeline should not run in dry-run")
        ),
    )

    exit_code = run_mp_api_daily_pipeline.main()

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "dry-run ok" in output


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (datetime(2026, 5, 8, 15, tzinfo=UTC), date(2026, 5, 8)),
        (datetime(2026, 5, 10, 15, tzinfo=UTC), date(2026, 5, 8)),
        (datetime(2026, 5, 11, 2, tzinfo=UTC), date(2026, 5, 8)),
        (datetime(2026, 5, 12, 15, tzinfo=UTC), date(2026, 5, 12)),
    ],
)
def test_default_target_date_uses_current_weekday_and_previous_friday_on_weekends(
    now: datetime,
    expected: date,
) -> None:
    assert run_mp_api_daily_pipeline._default_target_date(now) == expected  # noqa: SLF001


def test_daily_pipeline_rejects_weak_production_database_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = SimpleNamespace(
        target_date=date(2026, 5, 10),
        window_days=4,
        estado=None,
        refresh_only=False,
        dry_run=True,
        requested_by="unit_test",
        max_requests=3,
    )
    parser = SimpleNamespace(parse_args=lambda: args)
    app_settings = SimpleNamespace(
        app_env="production",
        database_url="postgresql+psycopg://postgres:postgres@localhost:5432/chilecompra",
    )

    monkeypatch.setattr(run_mp_api_daily_pipeline, "_parser", lambda: parser)
    monkeypatch.setattr(run_mp_api_daily_pipeline, "get_settings", lambda: app_settings)

    with pytest.raises(ValueError, match="requires a non-local DATABASE_URL host"):
        run_mp_api_daily_pipeline.main()


def test_sync_operator_recipes_explicitly_enable_mp_api() -> None:
    justfile_content = (REPO_ROOT / "justfile").read_text(encoding="utf-8")

    assert "mp-api-sync-active *args: db-up" in justfile_content
    assert (
        "-e MERCADO_PUBLICO_API_ENABLED=true backend uv run --no-sync python scripts/fetch_mp_api.py --mode active-discovery"
    ) in justfile_content
    assert "mp-api-sync-rolling *args: db-up" in justfile_content
    assert (
        "-e MERCADO_PUBLICO_API_ENABLED=true backend uv run --no-sync python scripts/fetch_mp_api.py --mode rolling-window"
    ) in justfile_content
    assert "mp-api-sync-detail *args: db-up" in justfile_content
    assert (
        "-e MERCADO_PUBLICO_API_ENABLED=true backend uv run --no-sync python scripts/fetch_mp_api.py --mode detail-by-codigo"
    ) in justfile_content
    assert "mp-api-daily-refresh *args: db-up" in justfile_content
    assert (
        "-e MERCADO_PUBLICO_API_ENABLED=true backend uv run --no-sync python scripts/run_mp_api_daily_pipeline.py"
    ) in justfile_content

#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
import sys
from pathlib import Path
from typing import Sequence, cast
from uuid import UUID

from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.config import (  # noqa: E402
    get_settings,
    validate_production_database_safety,
)
from backend.db.session import SessionLocal  # noqa: E402
from backend.pipeline.extract.mp_api_client import MercadoPublicoClient  # noqa: E402
from backend.pipeline.extract.mp_api_config import MercadoPublicoSettings, from_app_settings  # noqa: E402
from backend.integrations.mercado_publico import (  # noqa: E402
    create_sync_run,
    execute_sync_mode,
    mark_sync_run_completed,
    mark_sync_run_failed,
)
from backend.integrations.mercado_publico.sync import SyncMode  # noqa: E402


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value}") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mercado Publico notice sync operator entrypoint")
    parser.add_argument(
        "--mode",
        choices=["active-discovery", "rolling-window", "detail-by-codigo"],
        required=True,
        help="Sync mode to execute",
    )
    parser.add_argument(
        "--target-date",
        type=_parse_date,
        default=None,
        help="Anchor date in YYYY-MM-DD for rolling-window mode (defaults to today)",
    )
    parser.add_argument(
        "--start-date",
        type=_parse_date,
        default=None,
        help="Explicit start date (YYYY-MM-DD) for rolling-window mode",
    )
    parser.add_argument(
        "--end-date",
        type=_parse_date,
        default=None,
        help="Explicit end date (YYYY-MM-DD) for rolling-window mode",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=4,
        help="Rolling window size in days for rolling-window mode",
    )
    parser.add_argument(
        "--estado",
        default=None,
        help="Optional estado filter for rolling-window mode",
    )
    parser.add_argument(
        "--codigo",
        action="append",
        default=[],
        help="Notice code for detail-by-codigo mode (repeat flag for multiple codes)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and args without API calls or DB writes",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=None,
        help="Optional max number of upstream requests allowed in this run",
    )
    parser.add_argument(
        "--requested-by",
        default="local_cli",
        help="Operator provenance label persisted in run metadata",
    )
    return parser


def _resolve_mode(value: str) -> SyncMode:
    if value not in {"active-discovery", "rolling-window", "detail-by-codigo"}:
        raise ValueError(f"unsupported mode: {value}")
    return cast(SyncMode, value)


def _build_client_settings() -> MercadoPublicoSettings:
    app_settings = get_settings()
    validate_production_database_safety(app_settings.app_env, app_settings.database_url)
    mp_settings = from_app_settings(app_settings)
    return mp_settings


def _validate_production_database_safety(*, app_env: str, database_url: str) -> None:
    validate_production_database_safety(app_env, database_url)


def _resolve_rolling_window(
    *,
    mode: SyncMode,
    target_date: date | None,
    window_days: int,
    start_date: date | None,
    end_date: date | None,
) -> tuple[date | None, int]:
    if mode != "rolling-window":
        if start_date is not None or end_date is not None:
            raise ValueError("--start-date/--end-date only apply to --mode rolling-window")
        return target_date, window_days

    if window_days < 1:
        raise ValueError("--window-days must be >= 1")

    if start_date is None and end_date is None:
        return target_date, window_days
    if start_date is None or end_date is None:
        raise ValueError("--start-date and --end-date must be provided together")
    if end_date < start_date:
        raise ValueError("--end-date must be >= --start-date")

    derived_window_days = (end_date.toordinal() - start_date.toordinal()) + 1
    return end_date, derived_window_days


def _validate_runtime_mode(settings: MercadoPublicoSettings, *, dry_run: bool) -> None:
    if dry_run:
        return
    if not settings.enabled:
        raise ValueError("MERCADO_PUBLICO_API_ENABLED must be true to execute API sync")


def _print_summary(
    *,
    mode: SyncMode,
    run_id: str,
    requests: int,
    notices_seen: int,
    notices_skipped_missing_external_notice_code: int,
    snapshots_upserted: int,
    snapshots_inserted: int,
    snapshots_updated: int,
) -> None:
    print(
        "[mp-api-sync] "
        f"mode={mode} run_id={run_id} requests={requests} "
        f"notices_seen={notices_seen} "
        f"notices_skipped_missing_external_notice_code={notices_skipped_missing_external_notice_code} "
        f"snapshots_upserted={snapshots_upserted} snapshots_inserted={snapshots_inserted} "
        f"snapshots_updated={snapshots_updated}"
    )


def _execute_with_tracking(
    session: Session,
    *,
    client: MercadoPublicoClient,
    mode: SyncMode,
    target_date: date | None,
    window_days: int,
    estado: str | None,
    codigos: Sequence[str],
    requested_by: str = "local_cli",
    max_requests: int | None = None,
) -> int:
    run, step = create_sync_run(
        session,
        mode=mode,
        requested_by=requested_by,
        run_parameters={
            "target_date": str(target_date) if target_date is not None else None,
            "window_days": window_days,
            "estado": estado,
            "codigos": list(codigos),
            "requested_by": requested_by,
            "max_requests": max_requests,
        },
        config={
            "target_date": str(target_date) if target_date is not None else None,
            "window_days": window_days,
            "estado": estado,
            "codigos": list(codigos),
            "requested_by": requested_by,
            "max_requests": max_requests,
        },
    )
    try:
        summary = execute_sync_mode(
            session=session,
            client=client,
            pipeline_run_id=UUID(str(run.id)),
            mode=mode,
            anchor_day=target_date,
            window_days=window_days,
            estado=estado,
            codigos=codigos,
            max_requests=max_requests,
        )
        mark_sync_run_completed(run=run, step=step, summary=summary)
        session.commit()
        _print_summary(
            mode=summary.mode,
            run_id=str(run.id),
            requests=summary.requests,
            notices_seen=summary.notices_seen,
            notices_skipped_missing_external_notice_code=(
                summary.notices_skipped_missing_external_notice_code
            ),
            snapshots_upserted=summary.snapshots_upserted,
            snapshots_inserted=summary.snapshots_inserted,
            snapshots_updated=summary.snapshots_updated,
        )
        return 0
    except Exception as exc:
        session.rollback()
        mark_sync_run_failed(run=run, step=step, error_message=str(exc))
        session.commit()
        print(f"[mp-api-sync] mode={mode} run_id={run.id} status=failed error={str(exc)}")
        return 1


def main() -> int:
    args = _parser().parse_args()
    mode = _resolve_mode(args.mode)
    target_date, window_days = _resolve_rolling_window(
        mode=mode,
        target_date=args.target_date,
        window_days=args.window_days,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    settings = _build_client_settings()
    _validate_runtime_mode(settings, dry_run=args.dry_run)

    if args.dry_run:
        print(
            "[mp-api-sync] dry-run ok "
            f"mode={mode} base_url={settings.normalized_base_url} "
            f"target_date={target_date.isoformat() if target_date is not None else 'none'} "
            f"window_days={window_days} max_requests={args.max_requests} requested_by={args.requested_by}"
        )
        return 0

    client = MercadoPublicoClient(settings=settings)
    with SessionLocal() as session:
        return _execute_with_tracking(
            session,
            client=client,
            mode=mode,
            target_date=target_date,
            window_days=window_days,
            estado=args.estado,
            codigos=args.codigo,
            requested_by=args.requested_by,
            max_requests=args.max_requests,
        )


if __name__ == "__main__":
    raise SystemExit(main())

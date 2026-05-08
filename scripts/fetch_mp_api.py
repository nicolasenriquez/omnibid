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

from backend.core.config import get_settings  # noqa: E402
from backend.db.session import SessionLocal  # noqa: E402
from backend.integrations.mercado_publico import (  # noqa: E402
    MercadoPublicoClient,
    MercadoPublicoSettings,
    create_sync_run,
    execute_sync_mode,
    from_app_settings,
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
    return parser


def _resolve_mode(value: str) -> SyncMode:
    if value not in {"active-discovery", "rolling-window", "detail-by-codigo"}:
        raise ValueError(f"unsupported mode: {value}")
    return cast(SyncMode, value)


def _build_client_settings() -> MercadoPublicoSettings:
    app_settings = get_settings()
    mp_settings = from_app_settings(app_settings)
    return mp_settings


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
) -> int:
    run, step = create_sync_run(
        session,
        mode=mode,
        config={
            "target_date": str(target_date) if target_date is not None else None,
            "window_days": window_days,
            "estado": estado,
            "codigos": list(codigos),
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
    settings = _build_client_settings()
    _validate_runtime_mode(settings, dry_run=args.dry_run)

    if args.dry_run:
        print(
            "[mp-api-sync] dry-run ok "
            f"mode={mode} base_url={settings.normalized_base_url} window_days={args.window_days}"
        )
        return 0

    client = MercadoPublicoClient(settings=settings)
    with SessionLocal() as session:
        return _execute_with_tracking(
            session,
            client=client,
            mode=mode,
            target_date=args.target_date,
            window_days=args.window_days,
            estado=args.estado,
            codigos=args.codigo,
        )


if __name__ == "__main__":
    raise SystemExit(main())

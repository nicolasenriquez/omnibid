#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.config import (  # noqa: E402
    get_settings,
    validate_production_database_safety,
)
from backend.db.session import SessionLocal  # noqa: E402
from backend.integrations.mercado_publico import (  # noqa: E402
    MercadoPublicoClient,
    from_app_settings,
)
from backend.pipeline.application import run_mp_api_daily_notice_pipeline  # noqa: E402

SANTIAGO_TIMEZONE = ZoneInfo("America/Santiago")


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value}") from exc


def _default_target_date(now: datetime | None = None) -> date:
    current = (now or datetime.now(UTC)).astimezone(SANTIAGO_TIMEZONE).date()
    weekday = current.weekday()
    if weekday == 5:
        offset = 1
    elif weekday == 6:
        offset = 2
    else:
        offset = 0
    return current.fromordinal(current.toordinal() - offset)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mercado Publico daily pipeline: rolling sync + Silver notice refresh"
    )
    parser.add_argument(
        "--target-date",
        type=_parse_date,
        default=None,
        help="Anchor date in YYYY-MM-DD for rolling-window mode (defaults to the last business day)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=4,
        help="Rolling window size in days (default: 4)",
    )
    parser.add_argument(
        "--estado",
        default=None,
        help="Optional estado filter for rolling-window sync",
    )
    parser.add_argument(
        "--refresh-only",
        action="store_true",
        help="Skip upstream sync and refresh Silver notice rows from persisted snapshots",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and args without API calls or DB writes",
    )
    parser.add_argument(
        "--requested-by",
        default="local_cli",
        help="Operator provenance label persisted in run metadata",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=None,
        help="Optional max number of upstream requests allowed in this run",
    )
    return parser


def _print_summary(
    *,
    target_date: date,
    window_days: int,
    refresh_only: bool,
    run_id: str,
    source_file_id: str,
    requests: int,
    notices_seen: int,
    notices_skipped_missing_external_notice_code: int,
    snapshots_upserted: int,
    snapshots_inserted: int,
    snapshots_updated: int,
    detail_requests: int,
    detail_snapshots_upserted: int,
    notice_candidates: int,
    upserted_notices: int,
    payload_rows_seen: int,
    payload_rows_used: int,
    notice_purchase_order_links_inserted: int,
) -> None:
    print(
        "[mp-api-daily] "
        f"target_date={target_date.isoformat()} window_days={window_days} "
        f"refresh_only={str(refresh_only).lower()} run_id={run_id} source_file_id={source_file_id} "
        f"requests={requests} notices_seen={notices_seen} "
        f"notices_skipped_missing_external_notice_code={notices_skipped_missing_external_notice_code} "
        f"snapshots_upserted={snapshots_upserted} snapshots_inserted={snapshots_inserted} "
        f"snapshots_updated={snapshots_updated} "
        f"detail_requests={detail_requests} detail_snapshots_upserted={detail_snapshots_upserted} "
        f"notice_candidates={notice_candidates} upserted_notices={upserted_notices} "
        f"payload_rows_seen={payload_rows_seen} payload_rows_used={payload_rows_used} "
        f"notice_purchase_order_links_inserted={notice_purchase_order_links_inserted}"
    )


def main() -> int:
    args = _parser().parse_args()
    if args.window_days < 1:
        raise SystemExit("--window-days must be >= 1")

    target_date = args.target_date or _default_target_date()
    app_settings = get_settings()
    validate_production_database_safety(app_settings.app_env, app_settings.database_url)
    mp_settings = from_app_settings(app_settings)

    if args.dry_run:
        print(
            "[mp-api-daily] dry-run ok "
            f"target_date={target_date.isoformat()} window_days={args.window_days} "
            f"refresh_only={str(args.refresh_only).lower()} "
            f"max_requests={args.max_requests} requested_by={args.requested_by} "
            f"base_url={mp_settings.normalized_base_url}"
        )
        return 0

    if not args.refresh_only and not mp_settings.enabled:
        raise SystemExit("MERCADO_PUBLICO_API_ENABLED must be true for sync+refresh execution")

    client = MercadoPublicoClient(settings=mp_settings)
    with SessionLocal() as session:
        try:
            summary = run_mp_api_daily_notice_pipeline(
                session,
                client=client,
                target_date=target_date,
                window_days=args.window_days,
                estado=args.estado,
                refresh_only=args.refresh_only,
                requested_by=args.requested_by,
                max_requests=args.max_requests,
            )
            session.commit()
            _print_summary(
                target_date=target_date,
                window_days=args.window_days,
                refresh_only=args.refresh_only,
                run_id=str(summary.run_id),
                source_file_id=str(summary.source_file_id),
                requests=summary.sync_summary.requests,
                notices_seen=summary.sync_summary.notices_seen,
                notices_skipped_missing_external_notice_code=(
                    summary.sync_summary.notices_skipped_missing_external_notice_code
                ),
                snapshots_upserted=summary.sync_summary.snapshots_upserted,
                snapshots_inserted=summary.sync_summary.snapshots_inserted,
                snapshots_updated=summary.sync_summary.snapshots_updated,
                detail_requests=summary.detail_summary.requests,
                detail_snapshots_upserted=summary.detail_summary.snapshots_upserted,
                notice_candidates=summary.silver_summary.notice_candidates,
                upserted_notices=summary.silver_summary.upserted_notices,
                payload_rows_seen=summary.silver_summary.payload_rows_seen,
                payload_rows_used=summary.silver_summary.payload_rows_used,
                notice_purchase_order_links_inserted=(
                    summary.postprocess_summary.notice_purchase_order_links_inserted
                ),
            )
            return 0
        except Exception as exc:
            try:
                session.commit()
            except Exception:
                session.rollback()
            print(
                "[mp-api-daily] "
                f"target_date={target_date.isoformat()} status=failed error={str(exc)}"
            )
            return 1


if __name__ == "__main__":
    raise SystemExit(main())

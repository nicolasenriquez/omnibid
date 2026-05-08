#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.config import get_settings  # noqa: E402
from backend.db.session import SessionLocal  # noqa: E402
from backend.pipeline.worker import JobHandler, run_worker_once  # noqa: E402


def _default_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def _noop_handler(*, session: Session, job: dict[str, Any], ingestion_unit_id: Any) -> dict[str, Any]:
    _ = session, job
    return {"noop": True, "ingestion_unit_id": str(ingestion_unit_id)}


def _handler_registry() -> dict[str, JobHandler]:
    return {
        "noop": _noop_handler,
    }


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run ingestion queue worker loop")
    parser.add_argument(
        "--worker-id",
        default=_default_worker_id(),
        help="Worker identifier used for queue lock ownership",
    )
    parser.add_argument(
        "--once",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Run one claim cycle and exit (default: false)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=0,
        help="Optional safety cap for loop iterations when --once is false",
    )
    args = parser.parse_args()

    handlers = _handler_registry()
    iterations = 0
    while True:
        iterations += 1
        with SessionLocal() as session:
            outcome = run_worker_once(
                session,
                worker_id=args.worker_id,
                handlers=handlers,
                retry_delay_seconds=settings.ingestion_queue_retry_delay_seconds,
                max_attempts=settings.ingestion_queue_max_attempts,
            )
            session.commit()
        print(
            f"[ingestion-worker] action={outcome.action} job_id={outcome.job_id} "
            f"ingestion_unit_id={outcome.ingestion_unit_id} job_status={outcome.job_status}"
        )

        if args.once:
            return 0
        if args.max_iterations > 0 and iterations >= args.max_iterations:
            return 0
        time.sleep(settings.ingestion_queue_poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())

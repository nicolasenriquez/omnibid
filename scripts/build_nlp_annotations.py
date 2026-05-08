#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.config import get_settings  # noqa: E402
from backend.nlp.annotations import (  # noqa: E402
    build_nlp_annotation_bundle,
)
from backend.nlp.artifacts import row_hash_sha256  # noqa: E402
from backend.nlp.runtime import (  # noqa: E402
    IMPLEMENTED_SOURCE_PROFILE,
    normalize_source_profile,
    validate_nlp_runtime_contract,
)


def _iter_jsonl_records(path: str) -> Iterable[dict[str, Any]]:
    if path == "-":
        handle = sys.stdin
        close_handle = False
    else:
        handle = open(path, "r", encoding="utf-8")
        close_handle = True

    try:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            if not isinstance(record, dict):
                raise ValueError("input JSONL must contain JSON objects")
            yield record
    finally:
        if close_handle:
            handle.close()


def build_annotation_record(raw: dict[str, Any], source_file_id: UUID) -> dict[str, Any]:
    payload_hash = row_hash_sha256(raw)
    bundle = build_nlp_annotation_bundle(
        raw=raw,
        source_file_id=source_file_id,
        row_hash_sha256=payload_hash,
    )
    return {
        "source_file_id": str(source_file_id),
        "row_hash_sha256": payload_hash,
        "payloads": [
            {"kind": kind, "payload": payload}
            for kind, payload in bundle.items()
            if payload is not None
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build NLP annotation payloads from raw JSONL")
    parser.add_argument(
        "--input",
        default="-",
        help="Input JSONL file with raw procurement rows, or - for stdin",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Output JSONL file for annotation payloads, or - for stdout",
    )
    parser.add_argument(
        "--source-file-id",
        required=True,
        help="Source file UUID used to stamp generated annotation payloads",
    )
    parser.add_argument(
        "--source-profile",
        default=IMPLEMENTED_SOURCE_PROFILE,
        help="Source profile for runtime validation",
    )
    args = parser.parse_args()

    settings = get_settings()
    validate_nlp_runtime_contract(
        settings.database_url,
        settings.test_database_url,
        source_profile=normalize_source_profile(args.source_profile),
    )

    source_file_id = UUID(args.source_file_id)
    records = (
        build_annotation_record(raw=raw, source_file_id=source_file_id)
        for raw in _iter_jsonl_records(args.input)
    )

    if args.output == "-":
        output_handle = sys.stdout
        close_output = False
    else:
        output_handle = open(args.output, "w", encoding="utf-8")
        close_output = True

    try:
        for record in records:
            output_handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    finally:
        if close_output:
            output_handle.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

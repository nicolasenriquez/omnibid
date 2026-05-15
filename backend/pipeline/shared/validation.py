"""Pipeline stage-boundary validators — fail-fast contract checks.

These validators sit at pipeline stage boundaries (extract → transform → load)
and enforce structural contracts before data crosses stage boundaries.
"""

from __future__ import annotations

from typing import Any, Sequence


def validate_notice_before_persistence(
    notice: Any,
    *,
    source_mode: str,
    resource_key: str,
) -> None:
    """Validate a parsed LicitacionNotice before it enters the persistence layer.

    Raises ValueError with an actionable message on contract violation.
    """
    if notice is None:
        raise ValueError(
            f"notice persistence contract violation: "
            f"notice is None (source_mode={source_mode}, resource_key={resource_key})"
        )

    external_notice_code = getattr(notice, "external_notice_code", None)
    if not external_notice_code or str(external_notice_code).strip() == "":
        raise ValueError(
            f"notice persistence contract violation: "
            f"external_notice_code is missing or empty "
            f"(source_mode={source_mode}, resource_key={resource_key})"
        )


def validate_canonicalized_row_before_upsert(
    row: dict[str, Any],
    *,
    conflict_fields: Sequence[str],
    table_name: str,
) -> None:
    """Validate a canonicalized row before upsert into a normalized/silver table.

    Ensures all conflict (business key) fields are present and non-None.
    Raises ValueError on contract violation.
    """
    if not row:
        raise ValueError(
            f"canonicalized row upsert contract violation: "
            f"row is empty (table={table_name})"
        )

    missing_keys: list[str] = []
    for field in conflict_fields:
        if row.get(field) is None:
            missing_keys.append(field)

    if missing_keys:
        raise ValueError(
            f"canonicalized row upsert contract violation: "
            f"business key fields have NULL values for table {table_name}: "
            f"{', '.join(missing_keys)} "
            f"(conflict_fields={list(conflict_fields)})"
        )


def validate_no_duplicate_business_keys(
    rows: list[dict[str, Any]],
    *,
    conflict_fields: Sequence[str],
    table_name: str,
) -> None:
    """Validate that a batch of canonicalized rows has no duplicate business keys.

    Duplicate keys within a batch violate the upsert contract because
    the deduplication layer must receive unique keys.
    Raises ValueError with a summary of duplicates.
    """
    seen: dict[tuple[Any, ...], int] = {}
    duplicates: list[tuple[tuple[Any, ...], int, int]] = []

    for idx, row in enumerate(rows):
        key = tuple(row.get(field) for field in conflict_fields)
        if key in seen:
            duplicates.append((key, seen[key], idx))
        else:
            seen[key] = idx

    if duplicates:
        dup_summary = "; ".join(
            f"key={k!r} rows=[{first},{second}]" for k, first, second in duplicates[:5]
        )
        raise ValueError(
            f"canonicalized row upsert contract violation: "
            f"duplicate business keys in batch for table {table_name}: "
            f"{dup_summary} "
            f"(conflict_fields={list(conflict_fields)}, total_duplicates={len(duplicates)})"
        )

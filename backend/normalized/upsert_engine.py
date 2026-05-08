from __future__ import annotations

import os
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.nlp.embeddings import FORBIDDEN_SILVER_EMBEDDING_FIELDS

POSTGRES_MAX_BIND_PARAMS = int(os.getenv("NORMALIZED_MAX_BIND_PARAMS", "32767"))
POSTGRES_BIND_PARAM_SAFETY_MARGIN = 64
SILVER_FORBIDDEN_FEATURE_COLUMNS = {
    "opportunity_rank",
    "opportunity_score",
    "winnability_score",
    "convenience_score",
    "win_probability",
    "award_probability",
    "forecast_value",
    "forecast_label",
    "anomaly_verdict",
    "recommendation_score",
}
SILVER_FORBIDDEN_FEATURE_SUFFIXES = (
    "_score",
    "_probability",
    "_forecast",
    "_prediction",
    "_rank",
)
SILVER_FORBIDDEN_FEATURE_PREFIXES = ("future_",)
SILVER_ANNOTATION_TFIDF_REF_PREFIX = "tfidf://"
SILVER_ANNOTATION_FORBIDDEN_VECTOR_FIELDS = (
    "tfidf_vector",
    "tfidf_values",
    "tfidf_matrix",
)


def _has_material_payload_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def _is_textual_sql_type(column_type: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(
        column_type,
        (
            sa.String,
            sa.Text,
            sa.Unicode,
            sa.UnicodeText,
            sa.CHAR,
            sa.VARCHAR,
        ),
    )


def _is_json_sql_type(column_type: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(column_type, sa.JSON)


def _is_array_sql_type(column_type: sa.types.TypeEngine[Any]) -> bool:
    return isinstance(column_type, sa.ARRAY)


def _build_complete_only_update_expr(*, model: Any, stmt: Any, field: str) -> Any:
    current_value = getattr(model, field)
    incoming_value = getattr(stmt.excluded, field)

    # Preserve existing canonical text when incoming data is blank/whitespace.
    if _is_textual_sql_type(current_value.type):
        incoming_value = sa.func.nullif(sa.func.btrim(sa.cast(incoming_value, sa.Text)), "")
    elif _is_json_sql_type(current_value.type):
        incoming_jsonb = sa.cast(incoming_value, JSONB)
        blank_json = sa.or_(
            sa.and_(
                sa.func.jsonb_typeof(incoming_jsonb) == sa.literal("object"),
                incoming_jsonb == sa.text("'{}'::jsonb"),
            ),
            sa.and_(
                sa.func.jsonb_typeof(incoming_jsonb) == sa.literal("array"),
                incoming_jsonb == sa.text("'[]'::jsonb"),
            ),
        )
        incoming_value = sa.case((blank_json, None), else_=incoming_value)
    elif _is_array_sql_type(current_value.type):
        incoming_value = sa.case(
            (sa.func.coalesce(sa.func.array_length(incoming_value, 1), 0) == 0, None),
            else_=incoming_value,
        )

    return sa.func.coalesce(incoming_value, current_value)


def dedupe_rows(rows: list[dict[str, Any]], key_fields: list[str]) -> list[dict[str, Any]]:
    if not key_fields:
        raise ValueError("conflict key fields cannot be empty")

    latest_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key_values: list[Any] = []
        for field in key_fields:
            value = row.get(field)
            if value is None or value == "":
                raise ValueError(f"missing business key value for field '{field}'")
            key_values.append(value)
        key = tuple(key_values)
        latest_by_key[key] = row
    return list(latest_by_key.values())


def validate_silver_feature_guardrails(*, model: Any, payloads: list[dict[str, Any]]) -> None:
    table_name = str(getattr(model, "__tablename__", ""))
    if not table_name.startswith("silver_"):
        return

    for payload in payloads:
        if table_name.endswith("_text_ann"):
            tfidf_ref = payload.get("tfidf_artifact_ref")
            if _has_material_payload_value(tfidf_ref):
                if not isinstance(tfidf_ref, str) or not tfidf_ref.startswith(
                    SILVER_ANNOTATION_TFIDF_REF_PREFIX
                ):
                    raise ValueError(
                        f"silver annotation contract violation for {table_name}: "
                        "tfidf_artifact_ref must be a reference string starting with 'tfidf://'"
                    )
            vector_columns = sorted(
                field
                for field in payload
                if field in SILVER_ANNOTATION_FORBIDDEN_VECTOR_FIELDS
                and _has_material_payload_value(payload.get(field))
            )
            if vector_columns:
                vector_columns_csv = ", ".join(vector_columns)
                raise ValueError(
                    f"silver annotation contract violation for {table_name}: "
                    f"serialized TF-IDF vector columns are forbidden [{vector_columns_csv}]"
                )
            embedding_columns = sorted(
                field
                for field in payload
                if (
                    field in FORBIDDEN_SILVER_EMBEDDING_FIELDS
                    or "embedding" in field
                    or field.endswith("_vector")
                )
                and _has_material_payload_value(payload.get(field))
            )
            if embedding_columns:
                embedding_columns_csv = ", ".join(embedding_columns)
                raise ValueError(
                    f"silver annotation contract violation for {table_name}: "
                    f"embedding/vector fields are downstream-only [{embedding_columns_csv}]"
                )

        violations = sorted(
            field
            for field in payload
            if (
                field in SILVER_FORBIDDEN_FEATURE_COLUMNS
                or field.endswith(SILVER_FORBIDDEN_FEATURE_SUFFIXES)
                or field.startswith(SILVER_FORBIDDEN_FEATURE_PREFIXES)
            )
            and _has_material_payload_value(payload.get(field))
        )
        if not violations:
            continue
        violations_csv = ", ".join(violations)
        raise ValueError(
            f"silver leakage guardrail violation for {table_name}: "
            f"forbidden feature columns [{violations_csv}]"
        )


def calculate_max_rows_per_upsert(columns_per_row: int) -> int:
    if columns_per_row <= 0:
        raise ValueError("columns_per_row must be > 0")
    available_params = POSTGRES_MAX_BIND_PARAMS - POSTGRES_BIND_PARAM_SAFETY_MARGIN
    return max(1, available_params // columns_per_row)


def execute_single_upsert(
    session: Session,
    model: Any,
    payloads: list[dict[str, Any]],
    conflict_fields: list[str],
) -> None:
    stmt = pg_insert(model).values(payloads)

    update_fields = sorted(set(payloads[0].keys()) - set(conflict_fields) - {"created_at"})
    set_map = {
        field: _build_complete_only_update_expr(model=model, stmt=stmt, field=field)
        for field in update_fields
    }
    if "updated_at" in payloads[0]:
        set_map["updated_at"] = sa.func.now()

    if set_map:
        stmt = stmt.on_conflict_do_update(index_elements=conflict_fields, set_=set_map)
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=conflict_fields)

    session.execute(stmt)


def execute_payloads_with_retry(
    session: Session,
    model: Any,
    payloads: list[dict[str, Any]],
    conflict_fields: list[str],
    max_rows_per_stmt: int,
) -> None:
    for start in range(0, len(payloads), max_rows_per_stmt):
        batch_payloads = payloads[start : start + max_rows_per_stmt]
        try:
            # Keep each batch isolated so a driver limit only rolls back the failing batch.
            with session.begin_nested():
                execute_single_upsert(
                    session=session,
                    model=model,
                    payloads=batch_payloads,
                    conflict_fields=conflict_fields,
                )
        except OperationalError:
            # Split and retry when runtime/driver limits reject large statements.
            if len(batch_payloads) <= 1:
                raise
            smaller_max_rows = max(1, len(batch_payloads) // 2)
            execute_payloads_with_retry(
                session=session,
                model=model,
                payloads=batch_payloads,
                conflict_fields=conflict_fields,
                max_rows_per_stmt=smaller_max_rows,
            )


def upsert_rows(
    session: Session,
    model: Any,
    rows: list[dict[str, Any]],
    conflict_fields: list[str],
) -> int:
    if not rows:
        return 0

    payloads = dedupe_rows(rows, conflict_fields)
    validate_silver_feature_guardrails(model=model, payloads=payloads)
    missing_fields = [field for field in conflict_fields if field not in payloads[0]]
    if missing_fields:
        fields_csv = ", ".join(missing_fields)
        raise ValueError(f"conflict key fields missing from payload: {fields_csv}")

    columns_per_row = max(len(payload) for payload in payloads)
    max_rows_per_stmt = calculate_max_rows_per_upsert(columns_per_row)
    execute_payloads_with_retry(
        session=session,
        model=model,
        payloads=payloads,
        conflict_fields=conflict_fields,
        max_rows_per_stmt=max_rows_per_stmt,
    )
    return len(payloads)


def flush_if_needed(
    session: Session,
    model: Any,
    buffer_rows: list[dict[str, Any]],
    conflict_fields: list[str],
    chunk_size: int,
    *,
    force: bool = False,
) -> int:
    if not force and len(buffer_rows) < chunk_size:
        return 0
    if not buffer_rows:
        return 0
    upserted = upsert_rows(session, model, buffer_rows, conflict_fields)
    buffer_rows.clear()
    return upserted


def flush_remaining(
    session: Session,
    model: Any,
    buffer_rows: list[dict[str, Any]],
    conflict_fields: list[str],
) -> int:
    if not buffer_rows:
        return 0
    upserted = upsert_rows(session, model, buffer_rows, conflict_fields)
    buffer_rows.clear()
    return upserted

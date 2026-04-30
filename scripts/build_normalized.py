#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, cast

import sqlalchemy as sa
from sqlalchemy.exc import OperationalError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db.session import SessionLocal  # noqa: E402
from backend.models.raw import RawLicitacion, RawOrdenCompra  # noqa: E402
from backend.models.operational import DataQualityIssue, PipelineRun, PipelineRunStep  # noqa: E402
from backend.models.normalized import (  # noqa: E402
    NormalizedBuyer,
    NormalizedCategory,
    NormalizedLicitacion,
    NormalizedLicitacionItem,
    NormalizedOferta,
    NormalizedOrdenCompra,
    NormalizedOrdenCompraItem,
    NormalizedSupplier,
    SilverAwardOutcome,
    SilverBidSubmission,
    SilverBuyingOrg,
    SilverCategoryRef,
    SilverContractingUnit,
    SilverNotice,
    SilverNoticeLine,
    SilverNoticeLineTextAnn,
    SilverNoticeTextAnn,
    SilverNoticePurchaseOrderLink,
    SilverPurchaseOrder,
    SilverPurchaseOrderLine,
    SilverPurchaseOrderLineTextAnn,
    SilverSupplier,
    SilverSupplierParticipation,
)
from backend.normalized.transform import (  # noqa: E402
    build_buyer_domain_payload,
    build_category_domain_payload,
    build_licitacion_item_payload,
    build_licitacion_payload,
    build_oferta_payload,
    build_orden_compra_item_payload,
    build_orden_compra_payload,
    build_silver_award_outcome_payload,
    build_silver_bid_submission_payload,
    build_silver_buying_org_payload,
    build_silver_category_ref_payload,
    build_silver_contracting_unit_payload,
    build_silver_notice_line_payload,
    build_silver_notice_line_text_ann_payload,
    build_silver_notice_payload,
    build_silver_notice_text_ann_payload,
    build_silver_notice_purchase_order_link_payload,
    build_silver_purchase_order_line_payload,
    build_silver_purchase_order_line_text_ann_payload,
    build_silver_purchase_order_payload,
    build_silver_supplier_participation_payload,
    build_silver_supplier_payload,
    build_supplier_domain_payload,
    resolve_buyer_identity_key as transform_resolve_buyer_identity_key,
    resolve_buying_org_identity_key as transform_resolve_buying_org_identity_key,
    resolve_contracting_unit_identity_key as transform_resolve_contracting_unit_identity_key,
    resolve_category_identity_key as transform_resolve_category_identity_key,
    resolve_category_ref_identity_key as transform_resolve_category_ref_identity_key,
    resolve_supplier_identity_key as transform_resolve_supplier_identity_key,
)
from backend.observability.cli_ui import (  # noqa: E402
    create_progress,
    progress_write,
    timed_step,
)

LICITACIONES_CONFLICT_FIELDS = ["codigo_externo"]
LICITACION_ITEMS_CONFLICT_FIELDS = ["codigo_externo", "codigo_item"]
OFERTAS_CONFLICT_FIELDS = ["oferta_key_sha256"]
ORDENES_CONFLICT_FIELDS = ["codigo_oc"]
ORDENES_ITEMS_CONFLICT_FIELDS = ["codigo_oc", "id_item"]
BUYERS_CONFLICT_FIELDS = ["buyer_key"]
SUPPLIERS_CONFLICT_FIELDS = ["supplier_key"]
CATEGORIES_CONFLICT_FIELDS = ["category_key"]
SILVER_NOTICE_CONFLICT_FIELDS = ["notice_id"]
SILVER_NOTICE_LINE_CONFLICT_FIELDS = ["notice_id", "item_code"]
SILVER_BID_SUBMISSION_CONFLICT_FIELDS = ["bid_submission_id"]
SILVER_AWARD_OUTCOME_CONFLICT_FIELDS = ["award_outcome_id"]
SILVER_PURCHASE_ORDER_CONFLICT_FIELDS = ["purchase_order_id"]
SILVER_PURCHASE_ORDER_LINE_CONFLICT_FIELDS = ["purchase_order_id", "line_item_id"]
SILVER_BUYING_ORG_CONFLICT_FIELDS = ["buying_org_id"]
SILVER_CONTRACTING_UNIT_CONFLICT_FIELDS = ["contracting_unit_id"]
SILVER_SUPPLIER_CONFLICT_FIELDS = ["supplier_id"]
SILVER_CATEGORY_REF_CONFLICT_FIELDS = ["category_ref_id"]
SILVER_NOTICE_PURCHASE_ORDER_LINK_CONFLICT_FIELDS = ["notice_id", "purchase_order_id", "link_type"]
SILVER_SUPPLIER_PARTICIPATION_CONFLICT_FIELDS = ["supplier_id", "notice_id"]
SILVER_NOTICE_TEXT_ANN_CONFLICT_FIELDS = ["notice_id", "nlp_version"]
SILVER_NOTICE_LINE_TEXT_ANN_CONFLICT_FIELDS = ["notice_id", "item_code", "nlp_version"]
SILVER_PURCHASE_ORDER_LINE_TEXT_ANN_CONFLICT_FIELDS = ["purchase_order_id", "line_item_id", "nlp_version"]
POSTGRES_MAX_BIND_PARAMS = int(os.getenv("NORMALIZED_MAX_BIND_PARAMS", "32767"))
POSTGRES_BIND_PARAM_SAFETY_MARGIN = 64
QUALITY_GATE_POLICY_VERSION = "quality_gate_policy_v1"
QUALITY_GATE_ISSUE_TYPE_REJECTED_ROWS = "normalized_rejected_rows"
QUALITY_GATE_ISSUE_TYPE_MISSING_DOMAIN_IDENTITY = "normalized_missing_domain_identity"
QUALITY_GATE_SEVERITY_WARNING = "warning"
QUALITY_GATE_SEVERITY_ERROR = "error"
QUALITY_GATE_MAX_ERROR_RATE = 0.005
QUALITY_GATE_FAIL_ON_CRITICAL_ERROR = True
QUALITY_GATE_CRITICAL_ISSUE_TYPES = {QUALITY_GATE_ISSUE_TYPE_REJECTED_ROWS}
QUALITY_GATE_CHECKPOINT_EVERY_PAGES_DEFAULT = int(
    os.getenv("NORMALIZED_QUALITY_GATE_CHECKPOINT_EVERY_PAGES", "10")
)
QUALITY_GATE_MIN_ROWS_BEFORE_FAIL_FAST_DEFAULT = int(
    os.getenv("NORMALIZED_QUALITY_GATE_MIN_ROWS_BEFORE_FAIL_FAST", "100000")
)
QUALITY_GATE_ENTITY_TABLES = {
    "licitaciones": "normalized_licitaciones",
    "licitacion_items": "normalized_licitacion_items",
    "ofertas": "normalized_ofertas",
    "ordenes_compra": "normalized_ordenes_compra",
    "ordenes_compra_items": "normalized_ordenes_compra_items",
    "buyers": "normalized_buyers",
    "suppliers": "normalized_suppliers",
    "categories": "normalized_categories",
    "silver_notice": "silver_notice",
    "silver_notice_line": "silver_notice_line",
    "silver_bid_submission": "silver_bid_submission",
    "silver_award_outcome": "silver_award_outcome",
    "silver_purchase_order": "silver_purchase_order",
    "silver_purchase_order_line": "silver_purchase_order_line",
    "silver_buying_org": "silver_buying_org",
    "silver_contracting_unit": "silver_contracting_unit",
    "silver_supplier": "silver_supplier",
    "silver_category_ref": "silver_category_ref",
    "silver_notice_purchase_order_link": "silver_notice_purchase_order_link",
    "silver_supplier_participation": "silver_supplier_participation",
    "silver_notice_text_ann": "silver_notice_text_ann",
    "silver_notice_line_text_ann": "silver_notice_line_text_ann",
    "silver_purchase_order_line_text_ann": "silver_purchase_order_line_text_ann",
}
QUALITY_GATE_DOMAIN_IDENTITY_FIELDS = {
    "buyers": "codigo_unidad_compra",
    "suppliers": "codigo_proveedor_or_rut_proveedor",
    "categories": "codigo_categoria",
}
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


def resolve_buyer_identity_key(raw: dict[str, Any]) -> str | None:
    return transform_resolve_buyer_identity_key(raw)


def resolve_supplier_identity_key(raw: dict[str, Any]) -> str | None:
    return transform_resolve_supplier_identity_key(raw)


def resolve_category_identity_key(raw: dict[str, Any]) -> str | None:
    return transform_resolve_category_identity_key(raw)


def resolve_buying_org_identity_key(raw: dict[str, Any]) -> str | None:
    return transform_resolve_buying_org_identity_key(raw)


def resolve_contracting_unit_identity_key(raw: dict[str, Any]) -> str | None:
    return transform_resolve_contracting_unit_identity_key(raw)


def resolve_category_ref_identity_key(raw: dict[str, Any]) -> str | None:
    return transform_resolve_category_ref_identity_key(raw)


def build_supplier_domain_from_licitacion_transaction(
    *,
    raw: dict[str, Any],
    source_file_id: Any,
    oferta_payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if oferta_payload is None:
        return None
    oferta_payload["supplier_key"] = resolve_supplier_identity_key(raw)
    return build_supplier_domain_payload(
        raw=raw,
        source_file_id=source_file_id,
    )


def build_domain_payloads_from_orden_transaction(
    *,
    raw: dict[str, Any],
    source_file_id: Any,
    orden_payload: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if orden_payload is None:
        return None, None

    orden_payload["buyer_key"] = resolve_buyer_identity_key(raw)
    orden_payload["supplier_key"] = resolve_supplier_identity_key(raw)
    buyer_payload = build_buyer_domain_payload(
        raw=raw,
        source_file_id=source_file_id,
    )
    supplier_payload = build_supplier_domain_payload(
        raw=raw,
        source_file_id=source_file_id,
    )
    return buyer_payload, supplier_payload


def build_category_domain_from_orden_item_transaction(
    *,
    raw: dict[str, Any],
    source_file_id: Any,
    orden_item_payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if orden_item_payload is None:
        return None
    orden_item_payload["category_key"] = resolve_category_identity_key(raw)
    return build_category_domain_payload(
        raw=raw,
        source_file_id=source_file_id,
    )


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def create_normalized_run(session: Session, dataset: str, mode_label: str) -> tuple[PipelineRun, PipelineRunStep]:
    run = PipelineRun(
        run_key=f"normalized:{dataset}:{datetime.now(UTC).isoformat()}",
        dataset_type=dataset,
        status="running",
        config={
            "mode": mode_label,
            "quality_gate_policy_version": QUALITY_GATE_POLICY_VERSION,
        },
    )
    session.add(run)
    session.flush()

    step = PipelineRunStep(
        run_id=run.id,
        step_name="normalized_build",
        status="running",
    )
    session.add(step)
    session.flush()
    return run, step


def collect_normalized_quality_issues(
    entity_metrics: dict[str, dict[str, int]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for entity_name, metrics in entity_metrics.items():
        processed_rows = max(0, state_int(metrics.get("processed_rows"), 0))
        rejected_rows = max(0, state_int(metrics.get("rejected_rows"), 0))
        if rejected_rows <= 0:
            continue
        error_rate = (rejected_rows / processed_rows) if processed_rows > 0 else 0.0
        is_domain_identity_issue = entity_name in QUALITY_GATE_DOMAIN_IDENTITY_FIELDS
        identity_field = str(
            metrics.get("identity_field")
            or QUALITY_GATE_DOMAIN_IDENTITY_FIELDS.get(entity_name, "")
        )
        default_rejection_reason = "missing_identity" if is_domain_identity_issue else "rejected_rows"
        rejection_reason = str(metrics.get("rejection_reason") or default_rejection_reason)
        issue_type = (
            QUALITY_GATE_ISSUE_TYPE_MISSING_DOMAIN_IDENTITY
            if is_domain_identity_issue
            else QUALITY_GATE_ISSUE_TYPE_REJECTED_ROWS
        )
        issues.append(
            {
                "entity_name": entity_name,
                "table_name": QUALITY_GATE_ENTITY_TABLES.get(entity_name),
                "issue_type": issue_type,
                "severity": QUALITY_GATE_SEVERITY_WARNING,
                "record_ref": entity_name,
                "column_name": identity_field if is_domain_identity_issue else None,
                "details": {
                    "processed_rows": processed_rows,
                    "rejected_rows": rejected_rows,
                    "error_rate": error_rate,
                    "rejection_reason": rejection_reason,
                    "identity_field": identity_field if is_domain_identity_issue else None,
                },
            }
        )
    return issues


def persist_normalized_quality_issues(
    session: Session,
    run_id: Any,
    dataset: str,
    issues: list[dict[str, Any]],
) -> None:
    for issue in issues:
        quality_issue = DataQualityIssue(
            run_id=run_id,
            dataset_type=dataset,
            table_name=issue.get("table_name"),
            issue_type=issue["issue_type"],
            severity=issue["severity"],
            record_ref=issue.get("record_ref"),
            column_name=issue.get("column_name"),
            details=issue.get("details", {}),
        )
        session.add(quality_issue)
    session.flush()


def evaluate_normalized_quality_gate(
    entity_metrics: dict[str, dict[str, int]],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    total_processed_rows = sum(
        max(0, state_int(metrics.get("processed_rows"), 0)) for metrics in entity_metrics.values()
    )
    total_rejected_rows = sum(
        max(0, state_int(metrics.get("rejected_rows"), 0)) for metrics in entity_metrics.values()
    )
    dataset_error_rate = (
        (total_rejected_rows / total_processed_rows) if total_processed_rows > 0 else 0.0
    )
    critical_error_issue_exists = any(
        issue.get("severity") == QUALITY_GATE_SEVERITY_ERROR
        and issue.get("issue_type") in QUALITY_GATE_CRITICAL_ISSUE_TYPES
        for issue in issues
    )

    if QUALITY_GATE_FAIL_ON_CRITICAL_ERROR and critical_error_issue_exists:
        decision = "failed"
        decision_reason = "critical_error_issue_exists"
    elif dataset_error_rate > QUALITY_GATE_MAX_ERROR_RATE:
        decision = "failed"
        decision_reason = "dataset_error_rate_exceeded_threshold"
    elif issues:
        decision = "warning"
        decision_reason = "warning_issues_below_threshold"
    else:
        decision = "passed"
        decision_reason = "no_quality_issues"

    error_issues_count = sum(
        1 for issue in issues if issue.get("severity") == QUALITY_GATE_SEVERITY_ERROR
    )
    warning_issues_count = sum(
        1 for issue in issues if issue.get("severity") == QUALITY_GATE_SEVERITY_WARNING
    )

    return {
        "policy_version": QUALITY_GATE_POLICY_VERSION,
        "thresholds": {
            "max_error_rate": QUALITY_GATE_MAX_ERROR_RATE,
            "fail_on_critical_error": QUALITY_GATE_FAIL_ON_CRITICAL_ERROR,
            "critical_issue_types": sorted(QUALITY_GATE_CRITICAL_ISSUE_TYPES),
        },
        "issue_counts": {
            "total": len(issues),
            "error": error_issues_count,
            "warning": warning_issues_count,
        },
        "dataset_metrics": {
            "processed_rows": total_processed_rows,
            "rejected_rows": total_rejected_rows,
            "error_rate": dataset_error_rate,
        },
        "decision": decision,
        "decision_reason": decision_reason,
    }


def mark_normalized_run_completed(
    run: PipelineRun,
    step: PipelineRunStep,
    processed_rows: int,
    quality_gate: dict[str, Any],
) -> None:
    run_any = cast(Any, run)
    step_any = cast(Any, step)
    run_any.config = {
        **(run.config or {}),
        "quality_gate": quality_gate,
    }
    step_any.status = "completed"
    step_any.finished_at = datetime.now(UTC)
    step_any.rows_in = processed_rows
    step_any.rows_rejected = state_int(
        quality_gate.get("dataset_metrics", {}).get("rejected_rows"),
        0,
    )
    run_any.status = "completed"
    run_any.finished_at = datetime.now(UTC)


def mark_normalized_run_failed(
    run: PipelineRun,
    step: PipelineRunStep,
    error_summary: str,
    quality_gate: dict[str, Any] | None = None,
) -> None:
    run_any = cast(Any, run)
    step_any = cast(Any, step)
    error_details: dict[str, Any] = {"error": error_summary}
    if quality_gate is not None:
        error_details["quality_gate"] = quality_gate
        run_any.config = {
            **(run.config or {}),
            "quality_gate": quality_gate,
        }
    step_any.status = "failed"
    step_any.finished_at = datetime.now(UTC)
    step_any.error_details = error_details
    run_any.status = "failed"
    run_any.finished_at = datetime.now(UTC)
    run_any.error_summary = error_summary


def persist_failed_dataset_state(
    session: Session,
    state: dict[str, Any],
    dataset: str,
    snapshot: dict[str, int],
    state_path: Path,
) -> None:
    session.rollback()

    failed_state = state.get(dataset)
    if not isinstance(failed_state, dict):
        failed_state = {}
    failed_state["status"] = "failed"
    failed_state["source_total_rows"] = snapshot["total_rows"]
    failed_state["source_max_id"] = snapshot["max_id"]
    state[dataset] = failed_state
    save_state(state_path, state)


def raw_snapshot(session: Session, dataset: str, source_file_id: Any | None = None) -> dict[str, int]:
    if dataset == "licitacion":
        model: Any = RawLicitacion
    else:
        model = RawOrdenCompra
    filters = []
    if source_file_id is not None:
        filters.append(model.source_file_id == source_file_id)
    total_rows = session.execute(
        sa.select(sa.func.count()).select_from(model).where(*filters)
    ).scalar_one()
    max_id = session.execute(sa.select(sa.func.max(model.id)).where(*filters)).scalar_one()
    return {"total_rows": int(total_rows or 0), "max_id": int(max_id or 0)}


def should_skip_dataset(state: dict[str, Any], dataset: str, snapshot: dict[str, int]) -> bool:
    dataset_state = state.get(dataset)
    if not isinstance(dataset_state, dict):
        return False
    if dataset_state.get("status") != "completed":
        return False
    return (
        dataset_state.get("source_total_rows") == snapshot["total_rows"]
        and dataset_state.get("source_max_id") == snapshot["max_id"]
    )


def state_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def resolve_start_after_id(dataset_state: dict[str, Any] | None, incremental: bool) -> int:
    if not incremental:
        return 0
    if not isinstance(dataset_state, dict):
        return 0
    if "last_processed_raw_id" in dataset_state:
        return max(0, state_int(dataset_state.get("last_processed_raw_id"), 0))
    return 0


def table_row_count(session: Session, model: Any) -> int:
    return int(session.execute(sa.select(sa.func.count()).select_from(model)).scalar_one())


def _non_empty_text_expr(expr: Any) -> Any:
    return sa.func.nullif(sa.func.btrim(sa.cast(expr, sa.Text)), "")


def _json_first_non_empty_text(json_expr: Any, *keys: str) -> Any:
    candidates = [_non_empty_text_expr(json_expr[key].astext) for key in keys]
    return sa.func.coalesce(*candidates)


def _raw_subset_subquery(
    *,
    model: Any,
    start_after_id: int,
    limit_rows: int,
    name: str,
    source_file_id: Any | None = None,
) -> Any:
    stmt = (
        sa.select(model.id.label("id"), model.raw_json.label("raw_json"))
        .where(*_raw_scope_filters(model, start_after_id=start_after_id, source_file_id=source_file_id))
        .order_by(model.id.asc())
    )
    if limit_rows > 0:
        stmt = stmt.limit(limit_rows)
    return stmt.subquery(name)


def _raw_scope_filters(
    model: Any,
    *,
    start_after_id: int,
    source_file_id: Any | None = None,
) -> list[Any]:
    filters = [model.id > start_after_id]
    if source_file_id is not None:
        filters.append(model.source_file_id == source_file_id)
    return filters


def run_dataset_preflight_quality_audit(
    session: Session,
    *,
    dataset: str,
    start_after_id: int,
    limit_rows: int,
    source_file_id: Any | None = None,
) -> dict[str, Any]:
    if dataset == "licitacion":
        subset = _raw_subset_subquery(
            model=RawLicitacion,
            start_after_id=start_after_id,
            limit_rows=limit_rows,
            name="raw_licitaciones_subset",
            source_file_id=source_file_id,
        )
        raw_json = subset.c.raw_json
        has_codigo_externo = _json_first_non_empty_text(raw_json, "CodigoExterno").is_not(None)
        has_codigo = _json_first_non_empty_text(raw_json, "Codigo").is_not(None)
        has_item_code = _json_first_non_empty_text(raw_json, "Codigoitem", "CodigoItem").is_not(None)
        has_offer_signal = _json_first_non_empty_text(
            raw_json,
            "NombreProveedor",
            "Nombre de la Oferta",
            "Estado Oferta",
        ).is_not(None)
        has_supplier_identity = _json_first_non_empty_text(
            raw_json,
            "CodigoProveedor",
            "RutProveedor",
        ).is_not(None)

        licitacion_missing_keys = sa.not_(sa.and_(has_codigo_externo, has_codigo))
        item_missing_keys = sa.not_(sa.and_(has_codigo_externo, has_item_code))
        oferta_missing_supplier = sa.and_(
            has_codigo_externo,
            has_offer_signal,
            sa.not_(has_supplier_identity),
        )

        row = session.execute(
            sa.select(
                sa.func.count().label("scope_rows"),
                sa.func.count().filter(licitacion_missing_keys).label("licitacion_missing_keys"),
                sa.func.count().filter(item_missing_keys).label("item_missing_keys"),
                sa.func.count().filter(oferta_missing_supplier).label("oferta_missing_supplier"),
            ).select_from(subset)
        ).mappings().one()
        scope_rows = int(row["scope_rows"] or 0)
        checks = [
            {
                "name": "licitacion_missing_primary_keys",
                "rows": int(row["licitacion_missing_keys"] or 0),
            },
            {
                "name": "licitacion_item_missing_primary_keys",
                "rows": int(row["item_missing_keys"] or 0),
            },
            {
                "name": "oferta_missing_supplier_identity",
                "rows": int(row["oferta_missing_supplier"] or 0),
            },
        ]
    else:
        subset = _raw_subset_subquery(
            model=RawOrdenCompra,
            start_after_id=start_after_id,
            limit_rows=limit_rows,
            name="raw_ordenes_subset",
            source_file_id=source_file_id,
        )
        raw_json = subset.c.raw_json
        has_codigo = _json_first_non_empty_text(raw_json, "Codigo").is_not(None)
        has_item_code = _json_first_non_empty_text(raw_json, "IDItem").is_not(None)
        has_buyer_identity = _json_first_non_empty_text(raw_json, "CodigoUnidadCompra").is_not(None)
        has_supplier_identity = _json_first_non_empty_text(
            raw_json,
            "CodigoProveedor",
            "RutProveedor",
        ).is_not(None)
        has_category_identity = _json_first_non_empty_text(
            raw_json,
            "codigoCategoria",
            "codigoProductoONU",
            "CodigoProductoONU",
        ).is_not(None)

        buyer_missing = sa.and_(has_codigo, sa.not_(has_buyer_identity))
        supplier_missing = sa.and_(has_codigo, sa.not_(has_supplier_identity))
        category_missing_after_fallback = sa.and_(
            has_codigo,
            has_item_code,
            sa.not_(has_category_identity),
        )

        row = session.execute(
            sa.select(
                sa.func.count().label("scope_rows"),
                sa.func.count().filter(buyer_missing).label("buyer_missing"),
                sa.func.count().filter(supplier_missing).label("supplier_missing"),
                sa.func.count()
                .filter(category_missing_after_fallback)
                .label("category_missing_after_fallback"),
            ).select_from(subset)
        ).mappings().one()
        scope_rows = int(row["scope_rows"] or 0)
        checks = [
            {
                "name": "buyer_missing_identity",
                "rows": int(row["buyer_missing"] or 0),
            },
            {
                "name": "supplier_missing_identity",
                "rows": int(row["supplier_missing"] or 0),
            },
            {
                "name": "category_missing_identity_after_onu_fallback",
                "rows": int(row["category_missing_after_fallback"] or 0),
            },
        ]

    max_rate = 0.0
    for check in checks:
        rows = int(check["rows"])
        rate = (rows / scope_rows) if scope_rows > 0 else 0.0
        check["rate"] = rate
        if rate > max_rate:
            max_rate = rate

    return {
        "dataset": dataset,
        "scope_rows": scope_rows,
        "checks": checks,
        "max_rate": max_rate,
        "threshold": QUALITY_GATE_MAX_ERROR_RATE,
    }


def format_preflight_quality_audit(audit: dict[str, Any]) -> str:
    dataset = str(audit.get("dataset", "unknown"))
    scope_rows = state_int(audit.get("scope_rows"), 0)
    threshold = float(audit.get("threshold") or QUALITY_GATE_MAX_ERROR_RATE)
    checks = cast(list[dict[str, Any]], audit.get("checks") or [])
    check_parts: list[str] = []
    for check in checks:
        name = str(check.get("name", "unknown_check"))
        rows = state_int(check.get("rows"), 0)
        rate = float(check.get("rate") or 0.0)
        check_parts.append(f"{name}={rows:,} ({rate:.2%})")
    checks_joined = " | ".join(check_parts) if check_parts else "none"
    return (
        f"[normalized][preflight] dataset={dataset} scope_rows={scope_rows:,} "
        f"threshold={threshold:.2%} :: {checks_joined}"
    )


def close_stale_running_runs(session: Session, *, dataset: str) -> int:
    stale_runs = session.execute(
        sa.select(PipelineRun)
        .where(PipelineRun.dataset_type == dataset)
        .where(PipelineRun.status == "running")
    ).scalars().all()
    if not stale_runs:
        return 0

    stale_run_ids = [run.id for run in stale_runs]
    now_utc = datetime.now(UTC)
    for run in stale_runs:
        run_any = cast(Any, run)
        run_any.status = "failed"
        run_any.finished_at = now_utc
        run_any.error_summary = "stale running run auto-closed before new execution"

    stale_steps = session.execute(
        sa.select(PipelineRunStep)
        .where(PipelineRunStep.run_id.in_(stale_run_ids))
        .where(PipelineRunStep.status == "running")
    ).scalars().all()
    for step in stale_steps:
        step_any = cast(Any, step)
        step_any.status = "failed"
        step_any.finished_at = now_utc
        step_any.error_details = {
            **(step.error_details or {}),
            "error": "stale running step auto-closed before new execution",
        }
    return len(stale_runs)


def build_entity_metrics(
    *,
    processed_rows: int,
    accepted_rows: int,
    rejected_rows: int,
    deduplicated_rows: int,
    before_scope_rows: int,
    after_scope_rows: int,
) -> dict[str, int]:
    if processed_rows < 0:
        raise ValueError("processed_rows must be >= 0")
    if accepted_rows < 0:
        raise ValueError("accepted_rows must be >= 0")
    if rejected_rows < 0:
        raise ValueError("rejected_rows must be >= 0")
    if deduplicated_rows < 0:
        raise ValueError("deduplicated_rows must be >= 0")
    if before_scope_rows < 0:
        raise ValueError("before_scope_rows must be >= 0")
    if after_scope_rows < 0:
        raise ValueError("after_scope_rows must be >= 0")
    if after_scope_rows < before_scope_rows:
        raise ValueError("after_scope_rows must be >= before_scope_rows")
    if accepted_rows + rejected_rows != processed_rows:
        raise ValueError("accepted_rows + rejected_rows must equal processed_rows")
    if deduplicated_rows > accepted_rows:
        raise ValueError("deduplicated_rows cannot exceed accepted_rows")

    inserted_delta_rows = after_scope_rows - before_scope_rows
    if inserted_delta_rows > deduplicated_rows:
        raise ValueError("inserted_delta_rows cannot exceed deduplicated_rows")

    return {
        "processed_rows": processed_rows,
        "accepted_rows": accepted_rows,
        "rejected_rows": rejected_rows,
        "deduplicated_rows": deduplicated_rows,
        "inserted_delta_rows": inserted_delta_rows,
        "existing_or_updated_rows": deduplicated_rows - inserted_delta_rows,
        "scope_rows_before": before_scope_rows,
        "scope_rows_after": after_scope_rows,
    }


def build_domain_entity_metrics(
    *,
    accepted_rows: int,
    rejected_rows: int,
    deduplicated_rows: int,
    before_scope_rows: int,
    after_scope_rows: int,
) -> dict[str, int]:
    return build_entity_metrics(
        processed_rows=accepted_rows + rejected_rows,
        accepted_rows=accepted_rows,
        rejected_rows=rejected_rows,
        deduplicated_rows=deduplicated_rows,
        before_scope_rows=before_scope_rows,
        after_scope_rows=after_scope_rows,
    )


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
            if tfidf_ref is not None:
                if not isinstance(tfidf_ref, str) or not tfidf_ref.startswith(
                    SILVER_ANNOTATION_TFIDF_REF_PREFIX
                ):
                    raise ValueError(
                        f"silver annotation contract violation for {table_name}: "
                        "tfidf_artifact_ref must be a reference string starting with 'tfidf://'"
                    )
            vector_columns = sorted(
                field for field in payload if field in SILVER_ANNOTATION_FORBIDDEN_VECTOR_FIELDS
            )
            if vector_columns:
                vector_columns_csv = ", ".join(vector_columns)
                raise ValueError(
                    f"silver annotation contract violation for {table_name}: "
                    f"serialized TF-IDF vector columns are forbidden [{vector_columns_csv}]"
                )

        violations = sorted(
            field
            for field in payload
            if field in SILVER_FORBIDDEN_FEATURE_COLUMNS
            or field.endswith(SILVER_FORBIDDEN_FEATURE_SUFFIXES)
            or field.startswith(SILVER_FORBIDDEN_FEATURE_PREFIXES)
        )
        if not violations:
            continue
        violations_csv = ", ".join(violations)
        raise ValueError(
            f"silver leakage guardrail violation for {table_name}: "
            f"forbidden feature columns [{violations_csv}]"
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


def execute_single_upsert(
    session: Session,
    model: Any,
    payloads: list[dict[str, Any]],
    conflict_fields: list[str],
) -> None:
    stmt = pg_insert(model).values(payloads)

    update_fields = sorted(set(payloads[0].keys()) - set(conflict_fields) - {"created_at"})
    set_map = {field: getattr(stmt.excluded, field) for field in update_fields}
    if "updated_at" in payloads[0]:
        set_map["updated_at"] = sa.func.now()

    if set_map:
        stmt = stmt.on_conflict_do_update(index_elements=conflict_fields, set_=set_map)
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=conflict_fields)

    session.execute(stmt)


def calculate_max_rows_per_upsert(columns_per_row: int) -> int:
    if columns_per_row <= 0:
        raise ValueError("columns_per_row must be > 0")
    available_params = POSTGRES_MAX_BIND_PARAMS - POSTGRES_BIND_PARAM_SAFETY_MARGIN
    return max(1, available_params // columns_per_row)


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


def prune_orphan_notice_purchase_order_links(
    session: Session,
    notice_purchase_order_link_rows: list[dict[str, Any]],
) -> int:
    if not notice_purchase_order_link_rows:
        return 0

    purchase_order_ids = sorted(
        {
            purchase_order_id
            for row in notice_purchase_order_link_rows
            for purchase_order_id in [row.get("purchase_order_id")]
            if isinstance(purchase_order_id, str) and purchase_order_id.strip() != ""
        }
    )
    if not purchase_order_ids:
        dropped = len(notice_purchase_order_link_rows)
        notice_purchase_order_link_rows.clear()
        return dropped

    existing_purchase_order_ids: set[str] = set()
    batch_size = 1000
    for start in range(0, len(purchase_order_ids), batch_size):
        batch = purchase_order_ids[start : start + batch_size]
        existing_purchase_order_ids.update(
            session.execute(
                sa.select(SilverPurchaseOrder.purchase_order_id).where(
                    SilverPurchaseOrder.purchase_order_id.in_(batch)
                )
            )
            .scalars()
            .all()
        )

    if len(existing_purchase_order_ids) == len(purchase_order_ids):
        return 0

    filtered_rows = [
        row
        for row in notice_purchase_order_link_rows
        if row.get("purchase_order_id") in existing_purchase_order_ids
    ]
    dropped = len(notice_purchase_order_link_rows) - len(filtered_rows)
    if dropped > 0:
        notice_purchase_order_link_rows.clear()
        notice_purchase_order_link_rows.extend(filtered_rows)
    return dropped


def flush_licitaciones_chunk_buffers(
    *,
    session: Session,
    chunk_size: int,
    licitaciones_rows: list[dict[str, Any]],
    licitacion_items_rows: list[dict[str, Any]],
    suppliers_rows: list[dict[str, Any]],
    ofertas_rows: list[dict[str, Any]],
) -> tuple[int, int, int, int]:
    ofertas_chunk_triggered = len(ofertas_rows) >= chunk_size
    licitaciones = flush_if_needed(
        session,
        NormalizedLicitacion,
        licitaciones_rows,
        LICITACIONES_CONFLICT_FIELDS,
        chunk_size,
    )
    items = flush_if_needed(
        session,
        NormalizedLicitacionItem,
        licitacion_items_rows,
        LICITACION_ITEMS_CONFLICT_FIELDS,
        chunk_size,
    )
    # Supplier dimensions must exist before ofertas that reference supplier_key.
    suppliers = flush_if_needed(
        session,
        NormalizedSupplier,
        suppliers_rows,
        SUPPLIERS_CONFLICT_FIELDS,
        chunk_size,
        force=ofertas_chunk_triggered,
    )
    ofertas = flush_if_needed(
        session,
        NormalizedOferta,
        ofertas_rows,
        OFERTAS_CONFLICT_FIELDS,
        chunk_size,
    )
    return licitaciones, items, suppliers, ofertas


def flush_licitaciones_remaining_buffers(
    *,
    session: Session,
    licitaciones_rows: list[dict[str, Any]],
    licitacion_items_rows: list[dict[str, Any]],
    suppliers_rows: list[dict[str, Any]],
    ofertas_rows: list[dict[str, Any]],
) -> tuple[int, int, int, int]:
    licitaciones = flush_remaining(
        session,
        NormalizedLicitacion,
        licitaciones_rows,
        LICITACIONES_CONFLICT_FIELDS,
    )
    items = flush_remaining(
        session,
        NormalizedLicitacionItem,
        licitacion_items_rows,
        LICITACION_ITEMS_CONFLICT_FIELDS,
    )
    suppliers = flush_remaining(
        session,
        NormalizedSupplier,
        suppliers_rows,
        SUPPLIERS_CONFLICT_FIELDS,
    )
    ofertas = flush_remaining(
        session,
        NormalizedOferta,
        ofertas_rows,
        OFERTAS_CONFLICT_FIELDS,
    )
    return licitaciones, items, suppliers, ofertas


def flush_ordenes_chunk_buffers(
    *,
    session: Session,
    chunk_size: int,
    buyers_rows: list[dict[str, Any]],
    suppliers_rows: list[dict[str, Any]],
    categories_rows: list[dict[str, Any]],
    ordenes_rows: list[dict[str, Any]],
    ordenes_items_rows: list[dict[str, Any]],
) -> tuple[int, int, int, int, int]:
    facts_chunk_triggered = (
        len(ordenes_rows) >= chunk_size or len(ordenes_items_rows) >= chunk_size
    )
    # Dimension/domain entities must exist before fact rows with FK references.
    buyers = flush_if_needed(
        session,
        NormalizedBuyer,
        buyers_rows,
        BUYERS_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    suppliers = flush_if_needed(
        session,
        NormalizedSupplier,
        suppliers_rows,
        SUPPLIERS_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    categories = flush_if_needed(
        session,
        NormalizedCategory,
        categories_rows,
        CATEGORIES_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    ordenes = flush_if_needed(
        session,
        NormalizedOrdenCompra,
        ordenes_rows,
        ORDENES_CONFLICT_FIELDS,
        chunk_size,
    )
    ordenes_items = flush_if_needed(
        session,
        NormalizedOrdenCompraItem,
        ordenes_items_rows,
        ORDENES_ITEMS_CONFLICT_FIELDS,
        chunk_size,
    )
    return buyers, suppliers, categories, ordenes, ordenes_items


def flush_ordenes_remaining_buffers(
    *,
    session: Session,
    buyers_rows: list[dict[str, Any]],
    suppliers_rows: list[dict[str, Any]],
    categories_rows: list[dict[str, Any]],
    ordenes_rows: list[dict[str, Any]],
    ordenes_items_rows: list[dict[str, Any]],
) -> tuple[int, int, int, int, int]:
    buyers = flush_remaining(
        session,
        NormalizedBuyer,
        buyers_rows,
        BUYERS_CONFLICT_FIELDS,
    )
    suppliers = flush_remaining(
        session,
        NormalizedSupplier,
        suppliers_rows,
        SUPPLIERS_CONFLICT_FIELDS,
    )
    categories = flush_remaining(
        session,
        NormalizedCategory,
        categories_rows,
        CATEGORIES_CONFLICT_FIELDS,
    )
    ordenes = flush_remaining(
        session,
        NormalizedOrdenCompra,
        ordenes_rows,
        ORDENES_CONFLICT_FIELDS,
    )
    ordenes_items = flush_remaining(
        session,
        NormalizedOrdenCompraItem,
        ordenes_items_rows,
        ORDENES_ITEMS_CONFLICT_FIELDS,
    )
    return buyers, suppliers, categories, ordenes, ordenes_items


def flush_silver_licitaciones_chunk_buffers(
    *,
    session: Session,
    chunk_size: int,
    buying_org_rows: list[dict[str, Any]],
    contracting_unit_rows: list[dict[str, Any]],
    supplier_rows: list[dict[str, Any]],
    category_ref_rows: list[dict[str, Any]],
    notice_rows: list[dict[str, Any]],
    notice_line_rows: list[dict[str, Any]],
    bid_submission_rows: list[dict[str, Any]],
    award_outcome_rows: list[dict[str, Any]],
    supplier_participation_rows: list[dict[str, Any]],
    notice_text_ann_rows: list[dict[str, Any]],
    notice_line_text_ann_rows: list[dict[str, Any]],
) -> tuple[int, int, int, int, int, int, int, int, int, int, int]:
    facts_chunk_triggered = any(
        len(rows) >= chunk_size
        for rows in (
            notice_rows,
            notice_line_rows,
            bid_submission_rows,
            award_outcome_rows,
            supplier_participation_rows,
            notice_text_ann_rows,
            notice_line_text_ann_rows,
        )
    )
    buying_org = flush_if_needed(
        session,
        SilverBuyingOrg,
        buying_org_rows,
        SILVER_BUYING_ORG_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    contracting_unit = flush_if_needed(
        session,
        SilverContractingUnit,
        contracting_unit_rows,
        SILVER_CONTRACTING_UNIT_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    supplier = flush_if_needed(
        session,
        SilverSupplier,
        supplier_rows,
        SILVER_SUPPLIER_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    category_ref = flush_if_needed(
        session,
        SilverCategoryRef,
        category_ref_rows,
        SILVER_CATEGORY_REF_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    notice = flush_if_needed(
        session,
        SilverNotice,
        notice_rows,
        SILVER_NOTICE_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    notice_line = flush_if_needed(
        session,
        SilverNoticeLine,
        notice_line_rows,
        SILVER_NOTICE_LINE_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    bid_submission = flush_if_needed(
        session,
        SilverBidSubmission,
        bid_submission_rows,
        SILVER_BID_SUBMISSION_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    award_outcome = flush_if_needed(
        session,
        SilverAwardOutcome,
        award_outcome_rows,
        SILVER_AWARD_OUTCOME_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    supplier_participation = flush_if_needed(
        session,
        SilverSupplierParticipation,
        supplier_participation_rows,
        SILVER_SUPPLIER_PARTICIPATION_CONFLICT_FIELDS,
        chunk_size,
    )
    notice_text_ann = flush_if_needed(
        session,
        SilverNoticeTextAnn,
        notice_text_ann_rows,
        SILVER_NOTICE_TEXT_ANN_CONFLICT_FIELDS,
        chunk_size,
    )
    notice_line_text_ann = flush_if_needed(
        session,
        SilverNoticeLineTextAnn,
        notice_line_text_ann_rows,
        SILVER_NOTICE_LINE_TEXT_ANN_CONFLICT_FIELDS,
        chunk_size,
    )
    return (
        buying_org,
        contracting_unit,
        supplier,
        category_ref,
        notice,
        notice_line,
        bid_submission,
        award_outcome,
        supplier_participation,
        notice_text_ann,
        notice_line_text_ann,
    )


def flush_silver_licitaciones_remaining_buffers(
    *,
    session: Session,
    buying_org_rows: list[dict[str, Any]],
    contracting_unit_rows: list[dict[str, Any]],
    supplier_rows: list[dict[str, Any]],
    category_ref_rows: list[dict[str, Any]],
    notice_rows: list[dict[str, Any]],
    notice_line_rows: list[dict[str, Any]],
    bid_submission_rows: list[dict[str, Any]],
    award_outcome_rows: list[dict[str, Any]],
    supplier_participation_rows: list[dict[str, Any]],
    notice_text_ann_rows: list[dict[str, Any]],
    notice_line_text_ann_rows: list[dict[str, Any]],
) -> tuple[int, int, int, int, int, int, int, int, int, int, int]:
    buying_org = flush_remaining(
        session,
        SilverBuyingOrg,
        buying_org_rows,
        SILVER_BUYING_ORG_CONFLICT_FIELDS,
    )
    contracting_unit = flush_remaining(
        session,
        SilverContractingUnit,
        contracting_unit_rows,
        SILVER_CONTRACTING_UNIT_CONFLICT_FIELDS,
    )
    supplier = flush_remaining(
        session,
        SilverSupplier,
        supplier_rows,
        SILVER_SUPPLIER_CONFLICT_FIELDS,
    )
    category_ref = flush_remaining(
        session,
        SilverCategoryRef,
        category_ref_rows,
        SILVER_CATEGORY_REF_CONFLICT_FIELDS,
    )
    notice = flush_remaining(
        session,
        SilverNotice,
        notice_rows,
        SILVER_NOTICE_CONFLICT_FIELDS,
    )
    notice_line = flush_remaining(
        session,
        SilverNoticeLine,
        notice_line_rows,
        SILVER_NOTICE_LINE_CONFLICT_FIELDS,
    )
    bid_submission = flush_remaining(
        session,
        SilverBidSubmission,
        bid_submission_rows,
        SILVER_BID_SUBMISSION_CONFLICT_FIELDS,
    )
    award_outcome = flush_remaining(
        session,
        SilverAwardOutcome,
        award_outcome_rows,
        SILVER_AWARD_OUTCOME_CONFLICT_FIELDS,
    )
    supplier_participation = flush_remaining(
        session,
        SilverSupplierParticipation,
        supplier_participation_rows,
        SILVER_SUPPLIER_PARTICIPATION_CONFLICT_FIELDS,
    )
    notice_text_ann = flush_remaining(
        session,
        SilverNoticeTextAnn,
        notice_text_ann_rows,
        SILVER_NOTICE_TEXT_ANN_CONFLICT_FIELDS,
    )
    notice_line_text_ann = flush_remaining(
        session,
        SilverNoticeLineTextAnn,
        notice_line_text_ann_rows,
        SILVER_NOTICE_LINE_TEXT_ANN_CONFLICT_FIELDS,
    )
    return (
        buying_org,
        contracting_unit,
        supplier,
        category_ref,
        notice,
        notice_line,
        bid_submission,
        award_outcome,
        supplier_participation,
        notice_text_ann,
        notice_line_text_ann,
    )


def flush_silver_ordenes_chunk_buffers(
    *,
    session: Session,
    chunk_size: int,
    buying_org_rows: list[dict[str, Any]],
    contracting_unit_rows: list[dict[str, Any]],
    supplier_rows: list[dict[str, Any]],
    category_ref_rows: list[dict[str, Any]],
    purchase_order_rows: list[dict[str, Any]],
    purchase_order_line_rows: list[dict[str, Any]],
    notice_purchase_order_link_rows: list[dict[str, Any]],
    purchase_order_line_text_ann_rows: list[dict[str, Any]],
) -> tuple[int, int, int, int, int, int, int, int, int]:
    purchase_order_chunk_triggered = len(purchase_order_rows) >= chunk_size
    purchase_order_line_chunk_triggered = len(purchase_order_line_rows) >= chunk_size
    notice_purchase_order_link_chunk_triggered = len(notice_purchase_order_link_rows) >= chunk_size
    purchase_order_line_text_ann_chunk_triggered = (
        len(purchase_order_line_text_ann_rows) >= chunk_size
    )
    facts_chunk_triggered = (
        purchase_order_chunk_triggered
        or purchase_order_line_chunk_triggered
        or notice_purchase_order_link_chunk_triggered
        or purchase_order_line_text_ann_chunk_triggered
    )
    purchase_order_parent_chunk_triggered = facts_chunk_triggered
    purchase_order_line_parent_chunk_triggered = (
        purchase_order_line_chunk_triggered or purchase_order_line_text_ann_chunk_triggered
    )
    buying_org = flush_if_needed(
        session,
        SilverBuyingOrg,
        buying_org_rows,
        SILVER_BUYING_ORG_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    contracting_unit = flush_if_needed(
        session,
        SilverContractingUnit,
        contracting_unit_rows,
        SILVER_CONTRACTING_UNIT_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    supplier = flush_if_needed(
        session,
        SilverSupplier,
        supplier_rows,
        SILVER_SUPPLIER_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    category_ref = flush_if_needed(
        session,
        SilverCategoryRef,
        category_ref_rows,
        SILVER_CATEGORY_REF_CONFLICT_FIELDS,
        chunk_size,
        force=facts_chunk_triggered,
    )
    purchase_order = flush_if_needed(
        session,
        SilverPurchaseOrder,
        purchase_order_rows,
        SILVER_PURCHASE_ORDER_CONFLICT_FIELDS,
        chunk_size,
        force=purchase_order_parent_chunk_triggered,
    )
    purchase_order_line = flush_if_needed(
        session,
        SilverPurchaseOrderLine,
        purchase_order_line_rows,
        SILVER_PURCHASE_ORDER_LINE_CONFLICT_FIELDS,
        chunk_size,
        force=purchase_order_line_parent_chunk_triggered,
    )
    notice_purchase_order_link_rejected = 0
    if notice_purchase_order_link_chunk_triggered and notice_purchase_order_link_rows:
        notice_purchase_order_link_rejected = prune_orphan_notice_purchase_order_links(
            session,
            notice_purchase_order_link_rows,
        )
    notice_purchase_order_link = flush_if_needed(
        session,
        SilverNoticePurchaseOrderLink,
        notice_purchase_order_link_rows,
        SILVER_NOTICE_PURCHASE_ORDER_LINK_CONFLICT_FIELDS,
        chunk_size,
    )
    purchase_order_line_text_ann = flush_if_needed(
        session,
        SilverPurchaseOrderLineTextAnn,
        purchase_order_line_text_ann_rows,
        SILVER_PURCHASE_ORDER_LINE_TEXT_ANN_CONFLICT_FIELDS,
        chunk_size,
    )
    return (
        buying_org,
        contracting_unit,
        supplier,
        category_ref,
        purchase_order,
        purchase_order_line,
        notice_purchase_order_link,
        purchase_order_line_text_ann,
        notice_purchase_order_link_rejected,
    )


def flush_silver_ordenes_remaining_buffers(
    *,
    session: Session,
    buying_org_rows: list[dict[str, Any]],
    contracting_unit_rows: list[dict[str, Any]],
    supplier_rows: list[dict[str, Any]],
    category_ref_rows: list[dict[str, Any]],
    purchase_order_rows: list[dict[str, Any]],
    purchase_order_line_rows: list[dict[str, Any]],
    notice_purchase_order_link_rows: list[dict[str, Any]],
    purchase_order_line_text_ann_rows: list[dict[str, Any]],
) -> tuple[int, int, int, int, int, int, int, int, int]:
    buying_org = flush_remaining(
        session,
        SilverBuyingOrg,
        buying_org_rows,
        SILVER_BUYING_ORG_CONFLICT_FIELDS,
    )
    contracting_unit = flush_remaining(
        session,
        SilverContractingUnit,
        contracting_unit_rows,
        SILVER_CONTRACTING_UNIT_CONFLICT_FIELDS,
    )
    supplier = flush_remaining(
        session,
        SilverSupplier,
        supplier_rows,
        SILVER_SUPPLIER_CONFLICT_FIELDS,
    )
    category_ref = flush_remaining(
        session,
        SilverCategoryRef,
        category_ref_rows,
        SILVER_CATEGORY_REF_CONFLICT_FIELDS,
    )
    purchase_order = flush_remaining(
        session,
        SilverPurchaseOrder,
        purchase_order_rows,
        SILVER_PURCHASE_ORDER_CONFLICT_FIELDS,
    )
    purchase_order_line = flush_remaining(
        session,
        SilverPurchaseOrderLine,
        purchase_order_line_rows,
        SILVER_PURCHASE_ORDER_LINE_CONFLICT_FIELDS,
    )
    notice_purchase_order_link_rejected = prune_orphan_notice_purchase_order_links(
        session,
        notice_purchase_order_link_rows,
    )
    notice_purchase_order_link = flush_remaining(
        session,
        SilverNoticePurchaseOrderLink,
        notice_purchase_order_link_rows,
        SILVER_NOTICE_PURCHASE_ORDER_LINK_CONFLICT_FIELDS,
    )
    purchase_order_line_text_ann = flush_remaining(
        session,
        SilverPurchaseOrderLineTextAnn,
        purchase_order_line_text_ann_rows,
        SILVER_PURCHASE_ORDER_LINE_TEXT_ANN_CONFLICT_FIELDS,
    )
    return (
        buying_org,
        contracting_unit,
        supplier,
        category_ref,
        purchase_order,
        purchase_order_line,
        notice_purchase_order_link,
        purchase_order_line_text_ann,
        notice_purchase_order_link_rejected,
    )


def refresh_silver_notice_and_line_enrichments(session: Session) -> None:
    notice_line_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverNoticeLine)
        .where(SilverNoticeLine.notice_id == SilverNotice.notice_id)
        .scalar_subquery()
    )
    notice_bid_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverBidSubmission)
        .where(SilverBidSubmission.notice_id == SilverNotice.notice_id)
        .scalar_subquery()
    )
    notice_supplier_count_sq = (
        sa.select(sa.func.count(sa.distinct(SilverBidSubmission.supplier_key)))
        .select_from(SilverBidSubmission)
        .where(SilverBidSubmission.notice_id == SilverNotice.notice_id)
        .scalar_subquery()
    )
    notice_selected_bid_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverBidSubmission)
        .where(
            SilverBidSubmission.notice_id == SilverNotice.notice_id,
            SilverBidSubmission.selected_offer_flag.is_(True),
        )
        .scalar_subquery()
    )
    notice_awarded_line_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverAwardOutcome)
        .where(
            SilverAwardOutcome.notice_id == SilverNotice.notice_id,
            sa.or_(
                SilverAwardOutcome.selected_offer_flag.is_(True),
                SilverAwardOutcome.awarded_line_amount.is_not(None),
            ),
        )
        .scalar_subquery()
    )
    notice_purchase_order_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverNoticePurchaseOrderLink)
        .where(SilverNoticePurchaseOrderLink.notice_id == SilverNotice.notice_id)
        .scalar_subquery()
    )

    session.execute(
        sa.update(SilverNotice).values(
            notice_line_count=sa.func.coalesce(notice_line_count_sq, 0),
            notice_bid_count=sa.func.coalesce(notice_bid_count_sq, 0),
            notice_supplier_count=sa.func.coalesce(notice_supplier_count_sq, 0),
            notice_selected_bid_count=sa.func.coalesce(notice_selected_bid_count_sq, 0),
            notice_awarded_line_count=sa.func.coalesce(notice_awarded_line_count_sq, 0),
            notice_purchase_order_count=sa.func.coalesce(notice_purchase_order_count_sq, 0),
            notice_has_purchase_order_flag=sa.case(
                (sa.func.coalesce(notice_purchase_order_count_sq, 0) > 0, True),
                else_=False,
            ),
            notice_awarded_to_order_conversion_flag=sa.case(
                (
                    sa.and_(
                        sa.func.coalesce(notice_awarded_line_count_sq, 0) > 0,
                        sa.func.coalesce(notice_purchase_order_count_sq, 0) > 0,
                    ),
                    True,
                ),
                else_=False,
            ),
            updated_at=sa.func.now(),
        )
    )

    line_bid_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverBidSubmission)
        .where(
            SilverBidSubmission.notice_id == SilverNoticeLine.notice_id,
            SilverBidSubmission.item_code == SilverNoticeLine.item_code,
        )
        .scalar_subquery()
    )
    line_supplier_count_sq = (
        sa.select(sa.func.count(sa.distinct(SilverBidSubmission.supplier_key)))
        .select_from(SilverBidSubmission)
        .where(
            SilverBidSubmission.notice_id == SilverNoticeLine.notice_id,
            SilverBidSubmission.item_code == SilverNoticeLine.item_code,
        )
        .scalar_subquery()
    )
    line_min_offer_amount_sq = (
        sa.select(sa.func.min(SilverBidSubmission.total_price_offered))
        .where(
            SilverBidSubmission.notice_id == SilverNoticeLine.notice_id,
            SilverBidSubmission.item_code == SilverNoticeLine.item_code,
        )
        .scalar_subquery()
    )
    line_max_offer_amount_sq = (
        sa.select(sa.func.max(SilverBidSubmission.total_price_offered))
        .where(
            SilverBidSubmission.notice_id == SilverNoticeLine.notice_id,
            SilverBidSubmission.item_code == SilverNoticeLine.item_code,
        )
        .scalar_subquery()
    )
    line_avg_offer_amount_sq = (
        sa.select(sa.func.avg(SilverBidSubmission.total_price_offered))
        .where(
            SilverBidSubmission.notice_id == SilverNoticeLine.notice_id,
            SilverBidSubmission.item_code == SilverNoticeLine.item_code,
        )
        .scalar_subquery()
    )
    line_median_offer_amount_sq = (
        sa.select(
            sa.func.percentile_cont(0.5).within_group(SilverBidSubmission.total_price_offered)
        )
        .where(
            SilverBidSubmission.notice_id == SilverNoticeLine.notice_id,
            SilverBidSubmission.item_code == SilverNoticeLine.item_code,
        )
        .scalar_subquery()
    )

    session.execute(
        sa.update(SilverNoticeLine).values(
            line_bid_count=sa.func.coalesce(line_bid_count_sq, 0),
            line_supplier_count=sa.func.coalesce(line_supplier_count_sq, 0),
            line_min_offer_amount=line_min_offer_amount_sq,
            line_max_offer_amount=line_max_offer_amount_sq,
            line_avg_offer_amount=line_avg_offer_amount_sq,
            line_median_offer_amount=line_median_offer_amount_sq,
            line_price_dispersion_ratio=sa.case(
                (
                    sa.and_(
                        line_avg_offer_amount_sq.is_not(None),
                        line_avg_offer_amount_sq != 0,
                        line_min_offer_amount_sq.is_not(None),
                        line_max_offer_amount_sq.is_not(None),
                    ),
                    (line_max_offer_amount_sq - line_min_offer_amount_sq) / line_avg_offer_amount_sq,
                ),
                else_=None,
            ),
            updated_at=sa.func.now(),
        )
    )


def refresh_silver_purchase_order_enrichments(session: Session) -> None:
    line_count_sq = (
        sa.select(sa.func.count())
        .select_from(SilverPurchaseOrderLine)
        .where(SilverPurchaseOrderLine.purchase_order_id == SilverPurchaseOrder.purchase_order_id)
        .scalar_subquery()
    )
    total_quantity_sq = (
        sa.select(sa.func.sum(SilverPurchaseOrderLine.quantity_ordered))
        .where(SilverPurchaseOrderLine.purchase_order_id == SilverPurchaseOrder.purchase_order_id)
        .scalar_subquery()
    )
    total_net_amount_sq = (
        sa.select(sa.func.sum(SilverPurchaseOrderLine.line_net_total))
        .where(SilverPurchaseOrderLine.purchase_order_id == SilverPurchaseOrder.purchase_order_id)
        .scalar_subquery()
    )
    unique_product_count_sq = (
        sa.select(sa.func.count(sa.distinct(SilverPurchaseOrderLine.onu_product_code)))
        .where(SilverPurchaseOrderLine.purchase_order_id == SilverPurchaseOrder.purchase_order_id)
        .scalar_subquery()
    )

    session.execute(
        sa.update(SilverPurchaseOrder).values(
            purchase_order_line_count=sa.func.coalesce(line_count_sq, 0),
            purchase_order_total_quantity=total_quantity_sq,
            purchase_order_total_net_amount=total_net_amount_sq,
            purchase_order_unique_product_count=sa.func.coalesce(unique_product_count_sq, 0),
            is_linked_to_notice_flag=sa.case(
                (SilverPurchaseOrder.linked_notice_id.is_not(None), True),
                else_=False,
            ),
            updated_at=sa.func.now(),
        )
    )


def reconcile_silver_notice_purchase_order_links(session: Session) -> int:
    link_type = "explicit_code_match"
    insert_stmt = pg_insert(SilverNoticePurchaseOrderLink).from_select(
        [
            "notice_id",
            "purchase_order_id",
            "link_type",
            "link_confidence",
            "source_system",
            "source_file_id",
        ],
        sa.select(
            SilverPurchaseOrder.linked_notice_id.label("notice_id"),
            SilverPurchaseOrder.purchase_order_id.label("purchase_order_id"),
            sa.literal(link_type).label("link_type"),
            sa.literal(1).label("link_confidence"),
            sa.literal("mercado_publico_csv").label("source_system"),
            SilverPurchaseOrder.source_file_id.label("source_file_id"),
        )
        .join(
            SilverNotice,
            SilverNotice.notice_id == SilverPurchaseOrder.linked_notice_id,
        )
        .outerjoin(
            SilverNoticePurchaseOrderLink,
            sa.and_(
                SilverNoticePurchaseOrderLink.notice_id == SilverPurchaseOrder.linked_notice_id,
                SilverNoticePurchaseOrderLink.purchase_order_id
                == SilverPurchaseOrder.purchase_order_id,
                SilverNoticePurchaseOrderLink.link_type == link_type,
            ),
        )
        .where(
            SilverPurchaseOrder.linked_notice_id.is_not(None),
            SilverNoticePurchaseOrderLink.notice_purchase_order_link_id.is_(None),
        ),
    )
    insert_stmt = insert_stmt.on_conflict_do_nothing(
        index_elements=SILVER_NOTICE_PURCHASE_ORDER_LINK_CONFLICT_FIELDS
    )
    result = cast(Any, session.execute(insert_stmt))
    return max(0, int(result.rowcount or 0))


def process_licitaciones(
    session: Session,
    fetch_size: int,
    chunk_size: int,
    limit_rows: int,
    show_progress: bool,
    start_after_id: int = 0,
    source_file_id: Any | None = None,
    debug_telemetry: bool = False,
    state_checkpoint_every_pages: int = 1,
    on_checkpoint: Callable[[int, int], None] | None = None,
    on_quality_checkpoint: Callable[[int, int, dict[str, dict[str, Any]]], None] | None = None,
    quality_gate_checkpoint_every_pages: int = QUALITY_GATE_CHECKPOINT_EVERY_PAGES_DEFAULT,
) -> dict[str, Any]:
    licitaciones_before = table_row_count(session, NormalizedLicitacion)
    licitacion_items_before = table_row_count(session, NormalizedLicitacionItem)
    ofertas_before = table_row_count(session, NormalizedOferta)
    suppliers_before = table_row_count(session, NormalizedSupplier)
    silver_buying_org_before = table_row_count(session, SilverBuyingOrg)
    silver_contracting_unit_before = table_row_count(session, SilverContractingUnit)
    silver_supplier_before = table_row_count(session, SilverSupplier)
    silver_category_ref_before = table_row_count(session, SilverCategoryRef)
    silver_notice_before = table_row_count(session, SilverNotice)
    silver_notice_line_before = table_row_count(session, SilverNoticeLine)
    silver_bid_submission_before = table_row_count(session, SilverBidSubmission)
    silver_award_outcome_before = table_row_count(session, SilverAwardOutcome)
    silver_supplier_participation_before = table_row_count(session, SilverSupplierParticipation)
    silver_notice_text_ann_before = table_row_count(session, SilverNoticeTextAnn)
    silver_notice_line_text_ann_before = table_row_count(session, SilverNoticeLineTextAnn)

    total_rows = session.execute(
        sa.select(sa.func.count())
        .select_from(RawLicitacion)
        .where(
            *_raw_scope_filters(
                RawLicitacion,
                start_after_id=start_after_id,
                source_file_id=source_file_id,
            )
        )
    ).scalar_one()
    target_rows = min(total_rows, limit_rows) if limit_rows > 0 else total_rows

    progress_write(
        "[normalized] licitaciones raw rows "
        f"(delta id > {start_after_id:,}): {total_rows:,}, target: {target_rows:,}",
        enabled=show_progress,
    )

    last_id = start_after_id
    processed = 0

    licitaciones_rows: list[dict[str, Any]] = []
    licitacion_items_rows: list[dict[str, Any]] = []
    ofertas_rows: list[dict[str, Any]] = []
    suppliers_rows: list[dict[str, Any]] = []
    silver_buying_org_rows: list[dict[str, Any]] = []
    silver_contracting_unit_rows: list[dict[str, Any]] = []
    silver_supplier_rows: list[dict[str, Any]] = []
    silver_category_ref_rows: list[dict[str, Any]] = []
    silver_notice_rows: list[dict[str, Any]] = []
    silver_notice_line_rows: list[dict[str, Any]] = []
    silver_bid_submission_rows: list[dict[str, Any]] = []
    silver_award_outcome_rows: list[dict[str, Any]] = []
    silver_supplier_participation_rows: list[dict[str, Any]] = []
    silver_notice_text_ann_rows: list[dict[str, Any]] = []
    silver_notice_line_text_ann_rows: list[dict[str, Any]] = []
    licitaciones_accepted = 0
    licitacion_items_accepted = 0
    ofertas_accepted = 0
    suppliers_accepted = 0
    licitaciones_rejected = 0
    licitacion_items_rejected = 0
    ofertas_rejected = 0
    suppliers_rejected = 0
    licitaciones_deduplicated = 0
    licitacion_items_deduplicated = 0
    ofertas_deduplicated = 0
    suppliers_deduplicated = 0
    silver_buying_org_accepted = 0
    silver_contracting_unit_accepted = 0
    silver_supplier_accepted = 0
    silver_category_ref_accepted = 0
    silver_notice_accepted = 0
    silver_notice_line_accepted = 0
    silver_bid_submission_accepted = 0
    silver_award_outcome_accepted = 0
    silver_supplier_participation_accepted = 0
    silver_notice_text_ann_accepted = 0
    silver_notice_line_text_ann_accepted = 0
    silver_buying_org_rejected = 0
    silver_contracting_unit_rejected = 0
    silver_supplier_rejected = 0
    silver_category_ref_rejected = 0
    silver_notice_rejected = 0
    silver_notice_line_rejected = 0
    silver_bid_submission_rejected = 0
    silver_award_outcome_rejected = 0
    silver_supplier_participation_rejected = 0
    silver_notice_text_ann_rejected = 0
    silver_notice_line_text_ann_rejected = 0
    silver_buying_org_deduplicated = 0
    silver_contracting_unit_deduplicated = 0
    silver_supplier_deduplicated = 0
    silver_category_ref_deduplicated = 0
    silver_notice_deduplicated = 0
    silver_notice_line_deduplicated = 0
    silver_bid_submission_deduplicated = 0
    silver_award_outcome_deduplicated = 0
    silver_supplier_participation_deduplicated = 0
    silver_notice_text_ann_deduplicated = 0
    silver_notice_line_text_ann_deduplicated = 0

    row_bar = create_progress(
        total=target_rows,
        desc="normalized licitaciones",
        unit="rows",
        enabled=show_progress,
        leave=True,
        stage="normalized",
        footer=True,
        position=1,
    )
    checkpoint_every = max(10_000, fetch_size)
    next_checkpoint = checkpoint_every
    debug_checkpoint_every = checkpoint_every
    next_debug_checkpoint = debug_checkpoint_every
    pages_committed = 0
    quality_checkpoint_every_pages = max(1, quality_gate_checkpoint_every_pages)
    try:
        while True:
            if limit_rows > 0 and processed >= limit_rows:
                break

            page_limit = fetch_size
            if limit_rows > 0:
                remaining = limit_rows - processed
                if remaining < page_limit:
                    page_limit = remaining

            batch = (
                session.execute(
                    sa.select(RawLicitacion)
                    .where(
                        *_raw_scope_filters(
                            RawLicitacion,
                            start_after_id=last_id,
                            source_file_id=source_file_id,
                        )
                    )
                    .order_by(RawLicitacion.id.asc())
                    .limit(page_limit)
                )
                .scalars()
                .all()
            )
            if not batch:
                break

            for raw_row_obj in batch:
                raw_row = cast(Any, raw_row_obj)
                last_id = int(raw_row.id)
                processed += 1
                raw = cast(dict[str, Any], raw_row.raw_json or {})
                source_file_id = raw_row.source_file_id
                row_hash_sha256 = str(raw_row.row_hash_sha256)

                lic = build_licitacion_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if lic is not None:
                    licitaciones_rows.append(lic)
                    licitaciones_accepted += 1
                else:
                    licitaciones_rejected += 1

                lic_item = build_licitacion_item_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if lic_item is not None:
                    licitacion_items_rows.append(lic_item)
                    licitacion_items_accepted += 1
                else:
                    licitacion_items_rejected += 1

                oferta = build_oferta_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if oferta is not None:
                    ofertas_rows.append(oferta)
                    ofertas_accepted += 1
                else:
                    ofertas_rejected += 1

                supplier = build_supplier_domain_from_licitacion_transaction(
                    raw=raw,
                    source_file_id=source_file_id,
                    oferta_payload=oferta,
                )
                if supplier is not None:
                    suppliers_rows.append(supplier)
                    suppliers_accepted += 1
                elif oferta is not None:
                    suppliers_rejected += 1

                silver_notice = build_silver_notice_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if silver_notice is not None:
                    silver_notice_rows.append(silver_notice)
                    silver_notice_accepted += 1
                else:
                    silver_notice_rejected += 1

                silver_notice_line = build_silver_notice_line_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if silver_notice_line is not None:
                    silver_notice_line_rows.append(silver_notice_line)
                    silver_notice_line_accepted += 1
                else:
                    silver_notice_line_rejected += 1

                silver_bid_submission = build_silver_bid_submission_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if silver_bid_submission is not None:
                    silver_bid_submission_rows.append(silver_bid_submission)
                    silver_bid_submission_accepted += 1

                silver_award_outcome = build_silver_award_outcome_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if silver_award_outcome is not None:
                    silver_award_outcome_rows.append(silver_award_outcome)
                    silver_award_outcome_accepted += 1

                silver_buying_org = build_silver_buying_org_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                )
                if silver_buying_org is not None:
                    silver_buying_org_rows.append(silver_buying_org)
                    silver_buying_org_accepted += 1

                silver_contracting_unit = build_silver_contracting_unit_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                )
                if silver_contracting_unit is not None:
                    silver_contracting_unit_rows.append(silver_contracting_unit)
                    silver_contracting_unit_accepted += 1

                silver_supplier = build_silver_supplier_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                )
                if silver_supplier is not None:
                    silver_supplier_rows.append(silver_supplier)
                    silver_supplier_accepted += 1

                silver_category_ref = build_silver_category_ref_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                )
                if silver_category_ref is not None:
                    silver_category_ref_rows.append(silver_category_ref)
                    silver_category_ref_accepted += 1

                silver_supplier_participation = build_silver_supplier_participation_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    bid_submission_payload=silver_bid_submission,
                    award_outcome_payload=silver_award_outcome,
                )
                if silver_supplier_participation is not None:
                    silver_supplier_participation_rows.append(silver_supplier_participation)
                    silver_supplier_participation_accepted += 1

                silver_notice_text_ann = build_silver_notice_text_ann_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if silver_notice_text_ann is not None:
                    silver_notice_text_ann_rows.append(silver_notice_text_ann)
                    silver_notice_text_ann_accepted += 1
                else:
                    silver_notice_text_ann_rejected += 1

                silver_notice_line_text_ann = build_silver_notice_line_text_ann_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if silver_notice_line_text_ann is not None:
                    silver_notice_line_text_ann_rows.append(silver_notice_line_text_ann)
                    silver_notice_line_text_ann_accepted += 1
                else:
                    silver_notice_line_text_ann_rejected += 1

                (
                    chunk_licitaciones,
                    chunk_items,
                    chunk_suppliers,
                    chunk_ofertas,
                ) = flush_licitaciones_chunk_buffers(
                    session=session,
                    chunk_size=chunk_size,
                    licitaciones_rows=licitaciones_rows,
                    licitacion_items_rows=licitacion_items_rows,
                    suppliers_rows=suppliers_rows,
                    ofertas_rows=ofertas_rows,
                )
                licitaciones_deduplicated += chunk_licitaciones
                licitacion_items_deduplicated += chunk_items
                suppliers_deduplicated += chunk_suppliers
                ofertas_deduplicated += chunk_ofertas

                (
                    chunk_silver_buying_org,
                    chunk_silver_contracting_unit,
                    chunk_silver_supplier,
                    chunk_silver_category_ref,
                    chunk_silver_notice,
                    chunk_silver_notice_line,
                    chunk_silver_bid_submission,
                    chunk_silver_award_outcome,
                    chunk_silver_supplier_participation,
                    chunk_silver_notice_text_ann,
                    chunk_silver_notice_line_text_ann,
                ) = flush_silver_licitaciones_chunk_buffers(
                    session=session,
                    chunk_size=chunk_size,
                    buying_org_rows=silver_buying_org_rows,
                    contracting_unit_rows=silver_contracting_unit_rows,
                    supplier_rows=silver_supplier_rows,
                    category_ref_rows=silver_category_ref_rows,
                    notice_rows=silver_notice_rows,
                    notice_line_rows=silver_notice_line_rows,
                    bid_submission_rows=silver_bid_submission_rows,
                    award_outcome_rows=silver_award_outcome_rows,
                    supplier_participation_rows=silver_supplier_participation_rows,
                    notice_text_ann_rows=silver_notice_text_ann_rows,
                    notice_line_text_ann_rows=silver_notice_line_text_ann_rows,
                )
                silver_buying_org_deduplicated += chunk_silver_buying_org
                silver_contracting_unit_deduplicated += chunk_silver_contracting_unit
                silver_supplier_deduplicated += chunk_silver_supplier
                silver_category_ref_deduplicated += chunk_silver_category_ref
                silver_notice_deduplicated += chunk_silver_notice
                silver_notice_line_deduplicated += chunk_silver_notice_line
                silver_bid_submission_deduplicated += chunk_silver_bid_submission
                silver_award_outcome_deduplicated += chunk_silver_award_outcome
                silver_supplier_participation_deduplicated += chunk_silver_supplier_participation
                silver_notice_text_ann_deduplicated += chunk_silver_notice_text_ann
                silver_notice_line_text_ann_deduplicated += chunk_silver_notice_line_text_ann

            next_page_number = pages_committed + 1
            checkpoint_due = (
                on_checkpoint is not None
                and next_page_number % state_checkpoint_every_pages == 0
            )
            quality_checkpoint_due = (
                on_quality_checkpoint is not None
                and next_page_number % quality_checkpoint_every_pages == 0
            )
            if checkpoint_due:
                (
                    remaining_licitaciones_checkpoint,
                    remaining_items_checkpoint,
                    remaining_suppliers_checkpoint,
                    remaining_ofertas_checkpoint,
                ) = flush_licitaciones_remaining_buffers(
                    session=session,
                    licitaciones_rows=licitaciones_rows,
                    licitacion_items_rows=licitacion_items_rows,
                    suppliers_rows=suppliers_rows,
                    ofertas_rows=ofertas_rows,
                )
                licitaciones_deduplicated += remaining_licitaciones_checkpoint
                licitacion_items_deduplicated += remaining_items_checkpoint
                suppliers_deduplicated += remaining_suppliers_checkpoint
                ofertas_deduplicated += remaining_ofertas_checkpoint

                (
                    remaining_silver_buying_org_checkpoint,
                    remaining_silver_contracting_unit_checkpoint,
                    remaining_silver_supplier_checkpoint,
                    remaining_silver_category_ref_checkpoint,
                    remaining_silver_notice_checkpoint,
                    remaining_silver_notice_line_checkpoint,
                    remaining_silver_bid_submission_checkpoint,
                    remaining_silver_award_outcome_checkpoint,
                    remaining_silver_supplier_participation_checkpoint,
                    remaining_silver_notice_text_ann_checkpoint,
                    remaining_silver_notice_line_text_ann_checkpoint,
                ) = flush_silver_licitaciones_remaining_buffers(
                    session=session,
                    buying_org_rows=silver_buying_org_rows,
                    contracting_unit_rows=silver_contracting_unit_rows,
                    supplier_rows=silver_supplier_rows,
                    category_ref_rows=silver_category_ref_rows,
                    notice_rows=silver_notice_rows,
                    notice_line_rows=silver_notice_line_rows,
                    bid_submission_rows=silver_bid_submission_rows,
                    award_outcome_rows=silver_award_outcome_rows,
                    supplier_participation_rows=silver_supplier_participation_rows,
                    notice_text_ann_rows=silver_notice_text_ann_rows,
                    notice_line_text_ann_rows=silver_notice_line_text_ann_rows,
                )
                silver_buying_org_deduplicated += remaining_silver_buying_org_checkpoint
                silver_contracting_unit_deduplicated += remaining_silver_contracting_unit_checkpoint
                silver_supplier_deduplicated += remaining_silver_supplier_checkpoint
                silver_category_ref_deduplicated += remaining_silver_category_ref_checkpoint
                silver_notice_deduplicated += remaining_silver_notice_checkpoint
                silver_notice_line_deduplicated += remaining_silver_notice_line_checkpoint
                silver_bid_submission_deduplicated += remaining_silver_bid_submission_checkpoint
                silver_award_outcome_deduplicated += remaining_silver_award_outcome_checkpoint
                silver_supplier_participation_deduplicated += (
                    remaining_silver_supplier_participation_checkpoint
                )
                silver_notice_text_ann_deduplicated += remaining_silver_notice_text_ann_checkpoint
                silver_notice_line_text_ann_deduplicated += (
                    remaining_silver_notice_line_text_ann_checkpoint
                )

            session.commit()
            pages_committed = next_page_number
            if checkpoint_due:
                on_checkpoint(last_id, processed)
            if quality_checkpoint_due:
                on_quality_checkpoint(
                    last_id,
                    processed,
                    {
                        "licitaciones": {
                            "processed_rows": licitaciones_accepted + licitaciones_rejected,
                            "accepted_rows": licitaciones_accepted,
                            "rejected_rows": licitaciones_rejected,
                        },
                        "licitacion_items": {
                            "processed_rows": licitacion_items_accepted + licitacion_items_rejected,
                            "accepted_rows": licitacion_items_accepted,
                            "rejected_rows": licitacion_items_rejected,
                        },
                        "ofertas": {
                            "processed_rows": ofertas_accepted + ofertas_rejected,
                            "accepted_rows": ofertas_accepted,
                            "rejected_rows": ofertas_rejected,
                        },
                        "suppliers": {
                            "processed_rows": suppliers_accepted + suppliers_rejected,
                            "accepted_rows": suppliers_accepted,
                            "rejected_rows": suppliers_rejected,
                            "identity_field": QUALITY_GATE_DOMAIN_IDENTITY_FIELDS["suppliers"],
                            "rejection_reason": "missing_identity",
                        },
                        "silver_notice_text_ann": {
                            "processed_rows": silver_notice_text_ann_accepted + silver_notice_text_ann_rejected,
                            "accepted_rows": silver_notice_text_ann_accepted,
                            "rejected_rows": silver_notice_text_ann_rejected,
                        },
                        "silver_notice_line_text_ann": {
                            "processed_rows": silver_notice_line_text_ann_accepted
                            + silver_notice_line_text_ann_rejected,
                            "accepted_rows": silver_notice_line_text_ann_accepted,
                            "rejected_rows": silver_notice_line_text_ann_rejected,
                        },
                    },
                )
            if row_bar is not None:
                row_bar.update(len(batch))
            else:
                if processed >= next_checkpoint or processed == target_rows:
                    progress_write(
                        f"[normalized] licitaciones progress: {processed:,}/{target_rows:,}",
                        enabled=show_progress,
                    )
                    next_checkpoint += checkpoint_every
            if debug_telemetry and (processed >= next_debug_checkpoint or processed == target_rows):
                progress_write(
                    "[normalized][debug] licitaciones checkpoint: "
                    f"processed={processed:,} "
                    f"accepted(header/items/ofertas)="
                    f"{licitaciones_accepted:,}/{licitacion_items_accepted:,}/{ofertas_accepted:,} "
                    f"deduplicated(header/items/ofertas)="
                    f"{licitaciones_deduplicated:,}/{licitacion_items_deduplicated:,}/{ofertas_deduplicated:,}",
                    enabled=show_progress,
                )
                next_debug_checkpoint += debug_checkpoint_every

    finally:
        if row_bar is not None:
            row_bar.close()

    (
        remaining_licitaciones,
        remaining_items,
        remaining_suppliers,
        remaining_ofertas,
    ) = flush_licitaciones_remaining_buffers(
        session=session,
        licitaciones_rows=licitaciones_rows,
        licitacion_items_rows=licitacion_items_rows,
        suppliers_rows=suppliers_rows,
        ofertas_rows=ofertas_rows,
    )
    licitaciones_deduplicated += remaining_licitaciones
    licitacion_items_deduplicated += remaining_items
    suppliers_deduplicated += remaining_suppliers
    ofertas_deduplicated += remaining_ofertas

    (
        remaining_silver_buying_org,
        remaining_silver_contracting_unit,
        remaining_silver_supplier,
        remaining_silver_category_ref,
        remaining_silver_notice,
        remaining_silver_notice_line,
        remaining_silver_bid_submission,
        remaining_silver_award_outcome,
        remaining_silver_supplier_participation,
        remaining_silver_notice_text_ann,
        remaining_silver_notice_line_text_ann,
    ) = flush_silver_licitaciones_remaining_buffers(
        session=session,
        buying_org_rows=silver_buying_org_rows,
        contracting_unit_rows=silver_contracting_unit_rows,
        supplier_rows=silver_supplier_rows,
        category_ref_rows=silver_category_ref_rows,
        notice_rows=silver_notice_rows,
        notice_line_rows=silver_notice_line_rows,
        bid_submission_rows=silver_bid_submission_rows,
        award_outcome_rows=silver_award_outcome_rows,
        supplier_participation_rows=silver_supplier_participation_rows,
        notice_text_ann_rows=silver_notice_text_ann_rows,
        notice_line_text_ann_rows=silver_notice_line_text_ann_rows,
    )
    silver_buying_org_deduplicated += remaining_silver_buying_org
    silver_contracting_unit_deduplicated += remaining_silver_contracting_unit
    silver_supplier_deduplicated += remaining_silver_supplier
    silver_category_ref_deduplicated += remaining_silver_category_ref
    silver_notice_deduplicated += remaining_silver_notice
    silver_notice_line_deduplicated += remaining_silver_notice_line
    silver_bid_submission_deduplicated += remaining_silver_bid_submission
    silver_award_outcome_deduplicated += remaining_silver_award_outcome
    silver_supplier_participation_deduplicated += remaining_silver_supplier_participation
    silver_notice_text_ann_deduplicated += remaining_silver_notice_text_ann
    silver_notice_line_text_ann_deduplicated += remaining_silver_notice_line_text_ann

    reconcile_silver_notice_purchase_order_links(session)
    refresh_silver_notice_and_line_enrichments(session)

    session.commit()
    licitaciones_after = table_row_count(session, NormalizedLicitacion)
    licitacion_items_after = table_row_count(session, NormalizedLicitacionItem)
    ofertas_after = table_row_count(session, NormalizedOferta)
    suppliers_after = table_row_count(session, NormalizedSupplier)
    silver_buying_org_after = table_row_count(session, SilverBuyingOrg)
    silver_contracting_unit_after = table_row_count(session, SilverContractingUnit)
    silver_supplier_after = table_row_count(session, SilverSupplier)
    silver_category_ref_after = table_row_count(session, SilverCategoryRef)
    silver_notice_after = table_row_count(session, SilverNotice)
    silver_notice_line_after = table_row_count(session, SilverNoticeLine)
    silver_bid_submission_after = table_row_count(session, SilverBidSubmission)
    silver_award_outcome_after = table_row_count(session, SilverAwardOutcome)
    silver_supplier_participation_after = table_row_count(session, SilverSupplierParticipation)
    silver_notice_text_ann_after = table_row_count(session, SilverNoticeTextAnn)
    silver_notice_line_text_ann_after = table_row_count(session, SilverNoticeLineTextAnn)

    licitaciones_metrics = build_entity_metrics(
        processed_rows=processed,
        accepted_rows=licitaciones_accepted,
        rejected_rows=licitaciones_rejected,
        deduplicated_rows=licitaciones_deduplicated,
        before_scope_rows=licitaciones_before,
        after_scope_rows=licitaciones_after,
    )
    licitacion_items_metrics = build_entity_metrics(
        processed_rows=processed,
        accepted_rows=licitacion_items_accepted,
        rejected_rows=licitacion_items_rejected,
        deduplicated_rows=licitacion_items_deduplicated,
        before_scope_rows=licitacion_items_before,
        after_scope_rows=licitacion_items_after,
    )
    ofertas_metrics = build_entity_metrics(
        processed_rows=processed,
        accepted_rows=ofertas_accepted,
        rejected_rows=ofertas_rejected,
        deduplicated_rows=ofertas_deduplicated,
        before_scope_rows=ofertas_before,
        after_scope_rows=ofertas_after,
    )
    suppliers_metrics = build_domain_entity_metrics(
        accepted_rows=suppliers_accepted,
        rejected_rows=suppliers_rejected,
        deduplicated_rows=suppliers_deduplicated,
        before_scope_rows=suppliers_before,
        after_scope_rows=suppliers_after,
    )
    silver_buying_org_metrics = build_domain_entity_metrics(
        accepted_rows=silver_buying_org_accepted,
        rejected_rows=silver_buying_org_rejected,
        deduplicated_rows=silver_buying_org_deduplicated,
        before_scope_rows=silver_buying_org_before,
        after_scope_rows=silver_buying_org_after,
    )
    silver_contracting_unit_metrics = build_domain_entity_metrics(
        accepted_rows=silver_contracting_unit_accepted,
        rejected_rows=silver_contracting_unit_rejected,
        deduplicated_rows=silver_contracting_unit_deduplicated,
        before_scope_rows=silver_contracting_unit_before,
        after_scope_rows=silver_contracting_unit_after,
    )
    silver_supplier_metrics = build_domain_entity_metrics(
        accepted_rows=silver_supplier_accepted,
        rejected_rows=silver_supplier_rejected,
        deduplicated_rows=silver_supplier_deduplicated,
        before_scope_rows=silver_supplier_before,
        after_scope_rows=silver_supplier_after,
    )
    silver_category_ref_metrics = build_domain_entity_metrics(
        accepted_rows=silver_category_ref_accepted,
        rejected_rows=silver_category_ref_rejected,
        deduplicated_rows=silver_category_ref_deduplicated,
        before_scope_rows=silver_category_ref_before,
        after_scope_rows=silver_category_ref_after,
    )
    silver_notice_metrics = build_domain_entity_metrics(
        accepted_rows=silver_notice_accepted,
        rejected_rows=silver_notice_rejected,
        deduplicated_rows=silver_notice_deduplicated,
        before_scope_rows=silver_notice_before,
        after_scope_rows=silver_notice_after,
    )
    silver_notice_line_metrics = build_domain_entity_metrics(
        accepted_rows=silver_notice_line_accepted,
        rejected_rows=silver_notice_line_rejected,
        deduplicated_rows=silver_notice_line_deduplicated,
        before_scope_rows=silver_notice_line_before,
        after_scope_rows=silver_notice_line_after,
    )
    silver_bid_submission_metrics = build_domain_entity_metrics(
        accepted_rows=silver_bid_submission_accepted,
        rejected_rows=silver_bid_submission_rejected,
        deduplicated_rows=silver_bid_submission_deduplicated,
        before_scope_rows=silver_bid_submission_before,
        after_scope_rows=silver_bid_submission_after,
    )
    silver_award_outcome_metrics = build_domain_entity_metrics(
        accepted_rows=silver_award_outcome_accepted,
        rejected_rows=silver_award_outcome_rejected,
        deduplicated_rows=silver_award_outcome_deduplicated,
        before_scope_rows=silver_award_outcome_before,
        after_scope_rows=silver_award_outcome_after,
    )
    silver_supplier_participation_metrics = build_domain_entity_metrics(
        accepted_rows=silver_supplier_participation_accepted,
        rejected_rows=silver_supplier_participation_rejected,
        deduplicated_rows=silver_supplier_participation_deduplicated,
        before_scope_rows=silver_supplier_participation_before,
        after_scope_rows=silver_supplier_participation_after,
    )
    silver_notice_text_ann_metrics = build_domain_entity_metrics(
        accepted_rows=silver_notice_text_ann_accepted,
        rejected_rows=silver_notice_text_ann_rejected,
        deduplicated_rows=silver_notice_text_ann_deduplicated,
        before_scope_rows=silver_notice_text_ann_before,
        after_scope_rows=silver_notice_text_ann_after,
    )
    silver_notice_line_text_ann_metrics = build_domain_entity_metrics(
        accepted_rows=silver_notice_line_text_ann_accepted,
        rejected_rows=silver_notice_line_text_ann_rejected,
        deduplicated_rows=silver_notice_line_text_ann_deduplicated,
        before_scope_rows=silver_notice_line_text_ann_before,
        after_scope_rows=silver_notice_line_text_ann_after,
    )

    progress_write(
        "[normalized] licitaciones summary: "
        f"processed={processed:,}, "
        "header{"
        f"accepted={licitaciones_metrics['accepted_rows']:,} "
        f"deduplicated={licitaciones_metrics['deduplicated_rows']:,} "
        f"inserted_delta={licitaciones_metrics['inserted_delta_rows']:,} "
        f"existing_or_updated={licitaciones_metrics['existing_or_updated_rows']:,} "
        f"rejected={licitaciones_metrics['rejected_rows']:,}"
        "} "
        "items{"
        f"accepted={licitacion_items_metrics['accepted_rows']:,} "
        f"deduplicated={licitacion_items_metrics['deduplicated_rows']:,} "
        f"inserted_delta={licitacion_items_metrics['inserted_delta_rows']:,} "
        f"existing_or_updated={licitacion_items_metrics['existing_or_updated_rows']:,} "
        f"rejected={licitacion_items_metrics['rejected_rows']:,}"
        "} "
        "ofertas{"
        f"accepted={ofertas_metrics['accepted_rows']:,} "
        f"deduplicated={ofertas_metrics['deduplicated_rows']:,} "
        f"inserted_delta={ofertas_metrics['inserted_delta_rows']:,} "
        f"existing_or_updated={ofertas_metrics['existing_or_updated_rows']:,} "
        f"rejected={ofertas_metrics['rejected_rows']:,}"
        "} "
        "suppliers{"
        f"accepted={suppliers_metrics['accepted_rows']:,} "
        f"deduplicated={suppliers_metrics['deduplicated_rows']:,} "
        f"inserted_delta={suppliers_metrics['inserted_delta_rows']:,} "
        f"existing_or_updated={suppliers_metrics['existing_or_updated_rows']:,} "
        f"rejected={suppliers_metrics['rejected_rows']:,}"
        "} "
        "silver_core{"
        f"notice_deduplicated={silver_notice_metrics['deduplicated_rows']:,} "
        f"notice_line_deduplicated={silver_notice_line_metrics['deduplicated_rows']:,} "
        f"bid_deduplicated={silver_bid_submission_metrics['deduplicated_rows']:,} "
        f"award_deduplicated={silver_award_outcome_metrics['deduplicated_rows']:,}"
        "} "
        "silver_dims{"
        f"org_deduplicated={silver_buying_org_metrics['deduplicated_rows']:,} "
        f"unit_deduplicated={silver_contracting_unit_metrics['deduplicated_rows']:,} "
        f"supplier_deduplicated={silver_supplier_metrics['deduplicated_rows']:,} "
        f"category_deduplicated={silver_category_ref_metrics['deduplicated_rows']:,}"
        "} "
        "silver_links{"
        f"supplier_participation_deduplicated={silver_supplier_participation_metrics['deduplicated_rows']:,}"
        " annotations{"
        f"notice_text_ann_deduplicated={silver_notice_text_ann_metrics['deduplicated_rows']:,} "
        f"notice_line_text_ann_deduplicated={silver_notice_line_text_ann_metrics['deduplicated_rows']:,}"
        "}"
        "}",
        enabled=show_progress,
    )
    progress_write("[normalized] licitaciones done", enabled=show_progress)
    if on_checkpoint is not None:
        on_checkpoint(last_id, processed)
    return {
        "processed_rows": processed,
        "last_raw_id": last_id,
        "entity_metrics": {
            "licitaciones": licitaciones_metrics,
            "licitacion_items": licitacion_items_metrics,
            "ofertas": ofertas_metrics,
            "suppliers": suppliers_metrics,
            "silver_buying_org": silver_buying_org_metrics,
            "silver_contracting_unit": silver_contracting_unit_metrics,
            "silver_supplier": silver_supplier_metrics,
            "silver_category_ref": silver_category_ref_metrics,
            "silver_notice": silver_notice_metrics,
            "silver_notice_line": silver_notice_line_metrics,
            "silver_bid_submission": silver_bid_submission_metrics,
            "silver_award_outcome": silver_award_outcome_metrics,
            "silver_supplier_participation": silver_supplier_participation_metrics,
            "silver_notice_text_ann": silver_notice_text_ann_metrics,
            "silver_notice_line_text_ann": silver_notice_line_text_ann_metrics,
        },
    }


def process_ordenes_compra(
    session: Session,
    fetch_size: int,
    chunk_size: int,
    limit_rows: int,
    show_progress: bool,
    start_after_id: int = 0,
    source_file_id: Any | None = None,
    debug_telemetry: bool = False,
    state_checkpoint_every_pages: int = 1,
    on_checkpoint: Callable[[int, int], None] | None = None,
    on_quality_checkpoint: Callable[[int, int, dict[str, dict[str, Any]]], None] | None = None,
    quality_gate_checkpoint_every_pages: int = QUALITY_GATE_CHECKPOINT_EVERY_PAGES_DEFAULT,
) -> dict[str, Any]:
    ordenes_before = table_row_count(session, NormalizedOrdenCompra)
    ordenes_items_before = table_row_count(session, NormalizedOrdenCompraItem)
    buyers_before = table_row_count(session, NormalizedBuyer)
    suppliers_before = table_row_count(session, NormalizedSupplier)
    categories_before = table_row_count(session, NormalizedCategory)
    silver_buying_org_before = table_row_count(session, SilverBuyingOrg)
    silver_contracting_unit_before = table_row_count(session, SilverContractingUnit)
    silver_supplier_before = table_row_count(session, SilverSupplier)
    silver_category_ref_before = table_row_count(session, SilverCategoryRef)
    silver_purchase_order_before = table_row_count(session, SilverPurchaseOrder)
    silver_purchase_order_line_before = table_row_count(session, SilverPurchaseOrderLine)
    silver_notice_purchase_order_link_before = table_row_count(session, SilverNoticePurchaseOrderLink)
    silver_purchase_order_line_text_ann_before = table_row_count(
        session,
        SilverPurchaseOrderLineTextAnn,
    )
    existing_notice_ids = set(
        session.execute(sa.select(SilverNotice.notice_id)).scalars().all()
    )

    total_rows = session.execute(
        sa.select(sa.func.count())
        .select_from(RawOrdenCompra)
        .where(
            *_raw_scope_filters(
                RawOrdenCompra,
                start_after_id=start_after_id,
                source_file_id=source_file_id,
            )
        )
    ).scalar_one()
    target_rows = min(total_rows, limit_rows) if limit_rows > 0 else total_rows

    progress_write(
        "[normalized] ordenes_compra raw rows "
        f"(delta id > {start_after_id:,}): {total_rows:,}, target: {target_rows:,}",
        enabled=show_progress,
    )

    last_id = start_after_id
    processed = 0

    ordenes_rows: list[dict[str, Any]] = []
    ordenes_items_rows: list[dict[str, Any]] = []
    buyers_rows: list[dict[str, Any]] = []
    suppliers_rows: list[dict[str, Any]] = []
    categories_rows: list[dict[str, Any]] = []
    silver_buying_org_rows: list[dict[str, Any]] = []
    silver_contracting_unit_rows: list[dict[str, Any]] = []
    silver_supplier_rows: list[dict[str, Any]] = []
    silver_category_ref_rows: list[dict[str, Any]] = []
    silver_purchase_order_rows: list[dict[str, Any]] = []
    silver_purchase_order_line_rows: list[dict[str, Any]] = []
    silver_notice_purchase_order_link_rows: list[dict[str, Any]] = []
    silver_purchase_order_line_text_ann_rows: list[dict[str, Any]] = []
    ordenes_accepted = 0
    ordenes_items_accepted = 0
    buyers_accepted = 0
    suppliers_accepted = 0
    categories_accepted = 0
    ordenes_rejected = 0
    ordenes_items_rejected = 0
    buyers_rejected = 0
    suppliers_rejected = 0
    categories_rejected = 0
    ordenes_deduplicated = 0
    ordenes_items_deduplicated = 0
    buyers_deduplicated = 0
    suppliers_deduplicated = 0
    categories_deduplicated = 0
    silver_buying_org_accepted = 0
    silver_contracting_unit_accepted = 0
    silver_supplier_accepted = 0
    silver_category_ref_accepted = 0
    silver_purchase_order_accepted = 0
    silver_purchase_order_line_accepted = 0
    silver_notice_purchase_order_link_accepted = 0
    silver_purchase_order_line_text_ann_accepted = 0
    silver_buying_org_rejected = 0
    silver_contracting_unit_rejected = 0
    silver_supplier_rejected = 0
    silver_category_ref_rejected = 0
    silver_purchase_order_rejected = 0
    silver_purchase_order_line_rejected = 0
    silver_notice_purchase_order_link_rejected = 0
    silver_purchase_order_line_text_ann_rejected = 0
    silver_buying_org_deduplicated = 0
    silver_contracting_unit_deduplicated = 0
    silver_supplier_deduplicated = 0
    silver_category_ref_deduplicated = 0
    silver_purchase_order_deduplicated = 0
    silver_purchase_order_line_deduplicated = 0
    silver_notice_purchase_order_link_deduplicated = 0
    silver_purchase_order_line_text_ann_deduplicated = 0

    row_bar = create_progress(
        total=target_rows,
        desc="normalized ordenes_compra",
        unit="rows",
        enabled=show_progress,
        leave=True,
        stage="normalized",
        footer=True,
        position=1,
    )
    checkpoint_every = max(10_000, fetch_size)
    next_checkpoint = checkpoint_every
    debug_checkpoint_every = checkpoint_every
    next_debug_checkpoint = debug_checkpoint_every
    pages_committed = 0
    quality_checkpoint_every_pages = max(1, quality_gate_checkpoint_every_pages)
    try:
        while True:
            if limit_rows > 0 and processed >= limit_rows:
                break

            page_limit = fetch_size
            if limit_rows > 0:
                remaining = limit_rows - processed
                if remaining < page_limit:
                    page_limit = remaining

            batch = (
                session.execute(
                    sa.select(RawOrdenCompra)
                    .where(
                        *_raw_scope_filters(
                            RawOrdenCompra,
                            start_after_id=last_id,
                            source_file_id=source_file_id,
                        )
                    )
                    .order_by(RawOrdenCompra.id.asc())
                    .limit(page_limit)
                )
                .scalars()
                .all()
            )
            if not batch:
                break

            for raw_row_obj in batch:
                raw_row = cast(Any, raw_row_obj)
                last_id = int(raw_row.id)
                processed += 1
                raw = cast(dict[str, Any], raw_row.raw_json or {})
                source_file_id = raw_row.source_file_id
                row_hash_sha256 = str(raw_row.row_hash_sha256)

                orden = build_orden_compra_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if orden is not None:
                    ordenes_rows.append(orden)
                    ordenes_accepted += 1
                else:
                    ordenes_rejected += 1

                orden_item = build_orden_compra_item_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if orden_item is not None:
                    ordenes_items_rows.append(orden_item)
                    ordenes_items_accepted += 1
                else:
                    ordenes_items_rejected += 1

                buyer, supplier = build_domain_payloads_from_orden_transaction(
                    raw=raw,
                    source_file_id=source_file_id,
                    orden_payload=orden,
                )
                if buyer is not None:
                    buyers_rows.append(buyer)
                    buyers_accepted += 1
                elif orden is not None:
                    buyers_rejected += 1

                if supplier is not None:
                    suppliers_rows.append(supplier)
                    suppliers_accepted += 1
                elif orden is not None:
                    suppliers_rejected += 1

                category = build_category_domain_from_orden_item_transaction(
                    raw=raw,
                    source_file_id=source_file_id,
                    orden_item_payload=orden_item,
                )
                if category is not None:
                    categories_rows.append(category)
                    categories_accepted += 1
                elif orden_item is not None:
                    categories_rejected += 1

                silver_purchase_order = build_silver_purchase_order_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if silver_purchase_order is not None:
                    silver_purchase_order_rows.append(silver_purchase_order)
                    silver_purchase_order_accepted += 1
                else:
                    silver_purchase_order_rejected += 1

                silver_purchase_order_line = build_silver_purchase_order_line_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if silver_purchase_order_line is not None:
                    silver_purchase_order_line_rows.append(silver_purchase_order_line)
                    silver_purchase_order_line_accepted += 1
                else:
                    silver_purchase_order_line_rejected += 1

                silver_buying_org = build_silver_buying_org_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                )
                if silver_buying_org is not None:
                    silver_buying_org_rows.append(silver_buying_org)
                    silver_buying_org_accepted += 1

                silver_contracting_unit = build_silver_contracting_unit_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                )
                if silver_contracting_unit is not None:
                    silver_contracting_unit_rows.append(silver_contracting_unit)
                    silver_contracting_unit_accepted += 1

                silver_supplier = build_silver_supplier_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                )
                if silver_supplier is not None:
                    silver_supplier_rows.append(silver_supplier)
                    silver_supplier_accepted += 1

                silver_category_ref = build_silver_category_ref_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                )
                if silver_category_ref is not None:
                    silver_category_ref_rows.append(silver_category_ref)
                    silver_category_ref_accepted += 1

                silver_notice_purchase_order_link = build_silver_notice_purchase_order_link_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    purchase_order_payload=silver_purchase_order,
                )
                if silver_notice_purchase_order_link is not None:
                    notice_id = silver_notice_purchase_order_link.get("notice_id")
                    if isinstance(notice_id, str) and notice_id in existing_notice_ids:
                        silver_notice_purchase_order_link_rows.append(
                            silver_notice_purchase_order_link
                        )
                        silver_notice_purchase_order_link_accepted += 1

                silver_purchase_order_line_text_ann = build_silver_purchase_order_line_text_ann_payload(
                    raw=raw,
                    source_file_id=source_file_id,
                    row_hash_sha256=row_hash_sha256,
                )
                if silver_purchase_order_line_text_ann is not None:
                    silver_purchase_order_line_text_ann_rows.append(
                        silver_purchase_order_line_text_ann
                    )
                    silver_purchase_order_line_text_ann_accepted += 1
                else:
                    silver_purchase_order_line_text_ann_rejected += 1

                (
                    chunk_buyers,
                    chunk_suppliers,
                    chunk_categories,
                    chunk_ordenes,
                    chunk_ordenes_items,
                ) = flush_ordenes_chunk_buffers(
                    session=session,
                    chunk_size=chunk_size,
                    buyers_rows=buyers_rows,
                    suppliers_rows=suppliers_rows,
                    categories_rows=categories_rows,
                    ordenes_rows=ordenes_rows,
                    ordenes_items_rows=ordenes_items_rows,
                )
                buyers_deduplicated += chunk_buyers
                suppliers_deduplicated += chunk_suppliers
                categories_deduplicated += chunk_categories
                ordenes_deduplicated += chunk_ordenes
                ordenes_items_deduplicated += chunk_ordenes_items

                (
                    chunk_silver_buying_org,
                    chunk_silver_contracting_unit,
                    chunk_silver_supplier,
                    chunk_silver_category_ref,
                    chunk_silver_purchase_order,
                    chunk_silver_purchase_order_line,
                    chunk_silver_notice_purchase_order_link,
                    chunk_silver_purchase_order_line_text_ann,
                    chunk_silver_notice_purchase_order_link_rejected,
                ) = flush_silver_ordenes_chunk_buffers(
                    session=session,
                    chunk_size=chunk_size,
                    buying_org_rows=silver_buying_org_rows,
                    contracting_unit_rows=silver_contracting_unit_rows,
                    supplier_rows=silver_supplier_rows,
                    category_ref_rows=silver_category_ref_rows,
                    purchase_order_rows=silver_purchase_order_rows,
                    purchase_order_line_rows=silver_purchase_order_line_rows,
                    notice_purchase_order_link_rows=silver_notice_purchase_order_link_rows,
                    purchase_order_line_text_ann_rows=silver_purchase_order_line_text_ann_rows,
                )
                silver_buying_org_deduplicated += chunk_silver_buying_org
                silver_contracting_unit_deduplicated += chunk_silver_contracting_unit
                silver_supplier_deduplicated += chunk_silver_supplier
                silver_category_ref_deduplicated += chunk_silver_category_ref
                silver_purchase_order_deduplicated += chunk_silver_purchase_order
                silver_purchase_order_line_deduplicated += chunk_silver_purchase_order_line
                silver_notice_purchase_order_link_deduplicated += (
                    chunk_silver_notice_purchase_order_link
                )
                silver_notice_purchase_order_link_rejected += (
                    chunk_silver_notice_purchase_order_link_rejected
                )
                silver_purchase_order_line_text_ann_deduplicated += (
                    chunk_silver_purchase_order_line_text_ann
                )

            next_page_number = pages_committed + 1
            checkpoint_due = (
                on_checkpoint is not None
                and next_page_number % state_checkpoint_every_pages == 0
            )
            quality_checkpoint_due = (
                on_quality_checkpoint is not None
                and next_page_number % quality_checkpoint_every_pages == 0
            )
            if checkpoint_due:
                (
                    remaining_buyers_checkpoint,
                    remaining_suppliers_checkpoint,
                    remaining_categories_checkpoint,
                    remaining_ordenes_checkpoint,
                    remaining_ordenes_items_checkpoint,
                ) = flush_ordenes_remaining_buffers(
                    session=session,
                    buyers_rows=buyers_rows,
                    suppliers_rows=suppliers_rows,
                    categories_rows=categories_rows,
                    ordenes_rows=ordenes_rows,
                    ordenes_items_rows=ordenes_items_rows,
                )
                buyers_deduplicated += remaining_buyers_checkpoint
                suppliers_deduplicated += remaining_suppliers_checkpoint
                categories_deduplicated += remaining_categories_checkpoint
                ordenes_deduplicated += remaining_ordenes_checkpoint
                ordenes_items_deduplicated += remaining_ordenes_items_checkpoint

                (
                    remaining_silver_buying_org_checkpoint,
                    remaining_silver_contracting_unit_checkpoint,
                    remaining_silver_supplier_checkpoint,
                    remaining_silver_category_ref_checkpoint,
                    remaining_silver_purchase_order_checkpoint,
                    remaining_silver_purchase_order_line_checkpoint,
                    remaining_silver_notice_purchase_order_link_checkpoint,
                    remaining_silver_purchase_order_line_text_ann_checkpoint,
                    remaining_silver_notice_purchase_order_link_rejected_checkpoint,
                ) = flush_silver_ordenes_remaining_buffers(
                    session=session,
                    buying_org_rows=silver_buying_org_rows,
                    contracting_unit_rows=silver_contracting_unit_rows,
                    supplier_rows=silver_supplier_rows,
                    category_ref_rows=silver_category_ref_rows,
                    purchase_order_rows=silver_purchase_order_rows,
                    purchase_order_line_rows=silver_purchase_order_line_rows,
                    notice_purchase_order_link_rows=silver_notice_purchase_order_link_rows,
                    purchase_order_line_text_ann_rows=silver_purchase_order_line_text_ann_rows,
                )
                silver_buying_org_deduplicated += remaining_silver_buying_org_checkpoint
                silver_contracting_unit_deduplicated += remaining_silver_contracting_unit_checkpoint
                silver_supplier_deduplicated += remaining_silver_supplier_checkpoint
                silver_category_ref_deduplicated += remaining_silver_category_ref_checkpoint
                silver_purchase_order_deduplicated += remaining_silver_purchase_order_checkpoint
                silver_purchase_order_line_deduplicated += remaining_silver_purchase_order_line_checkpoint
                silver_notice_purchase_order_link_deduplicated += (
                    remaining_silver_notice_purchase_order_link_checkpoint
                )
                silver_purchase_order_line_text_ann_deduplicated += (
                    remaining_silver_purchase_order_line_text_ann_checkpoint
                )
                silver_notice_purchase_order_link_rejected += (
                    remaining_silver_notice_purchase_order_link_rejected_checkpoint
                )

            session.commit()
            pages_committed = next_page_number
            if checkpoint_due:
                on_checkpoint(last_id, processed)
            if quality_checkpoint_due:
                on_quality_checkpoint(
                    last_id,
                    processed,
                    {
                        "ordenes_compra": {
                            "processed_rows": ordenes_accepted + ordenes_rejected,
                            "accepted_rows": ordenes_accepted,
                            "rejected_rows": ordenes_rejected,
                        },
                        "ordenes_compra_items": {
                            "processed_rows": ordenes_items_accepted + ordenes_items_rejected,
                            "accepted_rows": ordenes_items_accepted,
                            "rejected_rows": ordenes_items_rejected,
                        },
                        "buyers": {
                            "processed_rows": buyers_accepted + buyers_rejected,
                            "accepted_rows": buyers_accepted,
                            "rejected_rows": buyers_rejected,
                            "identity_field": QUALITY_GATE_DOMAIN_IDENTITY_FIELDS["buyers"],
                            "rejection_reason": "missing_identity",
                        },
                        "suppliers": {
                            "processed_rows": suppliers_accepted + suppliers_rejected,
                            "accepted_rows": suppliers_accepted,
                            "rejected_rows": suppliers_rejected,
                            "identity_field": QUALITY_GATE_DOMAIN_IDENTITY_FIELDS["suppliers"],
                            "rejection_reason": "missing_identity",
                        },
                        "categories": {
                            "processed_rows": categories_accepted + categories_rejected,
                            "accepted_rows": categories_accepted,
                            "rejected_rows": categories_rejected,
                            "identity_field": QUALITY_GATE_DOMAIN_IDENTITY_FIELDS["categories"],
                            "rejection_reason": "missing_identity",
                        },
                        "silver_purchase_order": {
                            "processed_rows": silver_purchase_order_accepted + silver_purchase_order_rejected,
                            "accepted_rows": silver_purchase_order_accepted,
                            "rejected_rows": silver_purchase_order_rejected,
                        },
                        "silver_purchase_order_line": {
                            "processed_rows": silver_purchase_order_line_accepted
                            + silver_purchase_order_line_rejected,
                            "accepted_rows": silver_purchase_order_line_accepted,
                            "rejected_rows": silver_purchase_order_line_rejected,
                        },
                        "silver_notice_purchase_order_link": {
                            "processed_rows": silver_notice_purchase_order_link_accepted
                            + silver_notice_purchase_order_link_rejected,
                            "accepted_rows": silver_notice_purchase_order_link_accepted,
                            "rejected_rows": silver_notice_purchase_order_link_rejected,
                        },
                        "silver_purchase_order_line_text_ann": {
                            "processed_rows": silver_purchase_order_line_text_ann_accepted
                            + silver_purchase_order_line_text_ann_rejected,
                            "accepted_rows": silver_purchase_order_line_text_ann_accepted,
                            "rejected_rows": silver_purchase_order_line_text_ann_rejected,
                        },
                    },
                )
            if row_bar is not None:
                row_bar.update(len(batch))
            else:
                if processed >= next_checkpoint or processed == target_rows:
                    progress_write(
                        f"[normalized] ordenes_compra progress: {processed:,}/{target_rows:,}",
                        enabled=show_progress,
                    )
                    next_checkpoint += checkpoint_every
            if debug_telemetry and (processed >= next_debug_checkpoint or processed == target_rows):
                progress_write(
                    "[normalized][debug] ordenes_compra checkpoint: "
                    f"processed={processed:,} "
                    f"accepted(header/items)={ordenes_accepted:,}/{ordenes_items_accepted:,} "
                    f"deduplicated(header/items)={ordenes_deduplicated:,}/{ordenes_items_deduplicated:,}",
                    enabled=show_progress,
                )
                next_debug_checkpoint += debug_checkpoint_every

    finally:
        if row_bar is not None:
            row_bar.close()

    (
        remaining_buyers,
        remaining_suppliers,
        remaining_categories,
        remaining_ordenes,
        remaining_ordenes_items,
    ) = flush_ordenes_remaining_buffers(
        session=session,
        buyers_rows=buyers_rows,
        suppliers_rows=suppliers_rows,
        categories_rows=categories_rows,
        ordenes_rows=ordenes_rows,
        ordenes_items_rows=ordenes_items_rows,
    )
    buyers_deduplicated += remaining_buyers
    suppliers_deduplicated += remaining_suppliers
    categories_deduplicated += remaining_categories
    ordenes_deduplicated += remaining_ordenes
    ordenes_items_deduplicated += remaining_ordenes_items

    (
        remaining_silver_buying_org,
        remaining_silver_contracting_unit,
        remaining_silver_supplier,
        remaining_silver_category_ref,
        remaining_silver_purchase_order,
        remaining_silver_purchase_order_line,
        remaining_silver_notice_purchase_order_link,
        remaining_silver_purchase_order_line_text_ann,
        remaining_silver_notice_purchase_order_link_rejected,
    ) = flush_silver_ordenes_remaining_buffers(
        session=session,
        buying_org_rows=silver_buying_org_rows,
        contracting_unit_rows=silver_contracting_unit_rows,
        supplier_rows=silver_supplier_rows,
        category_ref_rows=silver_category_ref_rows,
        purchase_order_rows=silver_purchase_order_rows,
        purchase_order_line_rows=silver_purchase_order_line_rows,
        notice_purchase_order_link_rows=silver_notice_purchase_order_link_rows,
        purchase_order_line_text_ann_rows=silver_purchase_order_line_text_ann_rows,
    )
    silver_buying_org_deduplicated += remaining_silver_buying_org
    silver_contracting_unit_deduplicated += remaining_silver_contracting_unit
    silver_supplier_deduplicated += remaining_silver_supplier
    silver_category_ref_deduplicated += remaining_silver_category_ref
    silver_purchase_order_deduplicated += remaining_silver_purchase_order
    silver_purchase_order_line_deduplicated += remaining_silver_purchase_order_line
    silver_notice_purchase_order_link_deduplicated += remaining_silver_notice_purchase_order_link
    silver_purchase_order_line_text_ann_deduplicated += remaining_silver_purchase_order_line_text_ann
    silver_notice_purchase_order_link_rejected += remaining_silver_notice_purchase_order_link_rejected

    reconciled_notice_purchase_order_links = reconcile_silver_notice_purchase_order_links(session)
    silver_notice_purchase_order_link_accepted += reconciled_notice_purchase_order_links
    silver_notice_purchase_order_link_deduplicated += reconciled_notice_purchase_order_links

    refresh_silver_purchase_order_enrichments(session)
    refresh_silver_notice_and_line_enrichments(session)

    session.commit()
    ordenes_after = table_row_count(session, NormalizedOrdenCompra)
    ordenes_items_after = table_row_count(session, NormalizedOrdenCompraItem)
    buyers_after = table_row_count(session, NormalizedBuyer)
    suppliers_after = table_row_count(session, NormalizedSupplier)
    categories_after = table_row_count(session, NormalizedCategory)
    silver_buying_org_after = table_row_count(session, SilverBuyingOrg)
    silver_contracting_unit_after = table_row_count(session, SilverContractingUnit)
    silver_supplier_after = table_row_count(session, SilverSupplier)
    silver_category_ref_after = table_row_count(session, SilverCategoryRef)
    silver_purchase_order_after = table_row_count(session, SilverPurchaseOrder)
    silver_purchase_order_line_after = table_row_count(session, SilverPurchaseOrderLine)
    silver_notice_purchase_order_link_after = table_row_count(session, SilverNoticePurchaseOrderLink)
    silver_purchase_order_line_text_ann_after = table_row_count(session, SilverPurchaseOrderLineTextAnn)

    ordenes_metrics = build_entity_metrics(
        processed_rows=processed,
        accepted_rows=ordenes_accepted,
        rejected_rows=ordenes_rejected,
        deduplicated_rows=ordenes_deduplicated,
        before_scope_rows=ordenes_before,
        after_scope_rows=ordenes_after,
    )
    ordenes_items_metrics = build_entity_metrics(
        processed_rows=processed,
        accepted_rows=ordenes_items_accepted,
        rejected_rows=ordenes_items_rejected,
        deduplicated_rows=ordenes_items_deduplicated,
        before_scope_rows=ordenes_items_before,
        after_scope_rows=ordenes_items_after,
    )
    buyers_metrics = build_domain_entity_metrics(
        accepted_rows=buyers_accepted,
        rejected_rows=buyers_rejected,
        deduplicated_rows=buyers_deduplicated,
        before_scope_rows=buyers_before,
        after_scope_rows=buyers_after,
    )
    suppliers_metrics = build_domain_entity_metrics(
        accepted_rows=suppliers_accepted,
        rejected_rows=suppliers_rejected,
        deduplicated_rows=suppliers_deduplicated,
        before_scope_rows=suppliers_before,
        after_scope_rows=suppliers_after,
    )
    categories_metrics = build_domain_entity_metrics(
        accepted_rows=categories_accepted,
        rejected_rows=categories_rejected,
        deduplicated_rows=categories_deduplicated,
        before_scope_rows=categories_before,
        after_scope_rows=categories_after,
    )
    silver_buying_org_metrics = build_domain_entity_metrics(
        accepted_rows=silver_buying_org_accepted,
        rejected_rows=silver_buying_org_rejected,
        deduplicated_rows=silver_buying_org_deduplicated,
        before_scope_rows=silver_buying_org_before,
        after_scope_rows=silver_buying_org_after,
    )
    silver_contracting_unit_metrics = build_domain_entity_metrics(
        accepted_rows=silver_contracting_unit_accepted,
        rejected_rows=silver_contracting_unit_rejected,
        deduplicated_rows=silver_contracting_unit_deduplicated,
        before_scope_rows=silver_contracting_unit_before,
        after_scope_rows=silver_contracting_unit_after,
    )
    silver_supplier_metrics = build_domain_entity_metrics(
        accepted_rows=silver_supplier_accepted,
        rejected_rows=silver_supplier_rejected,
        deduplicated_rows=silver_supplier_deduplicated,
        before_scope_rows=silver_supplier_before,
        after_scope_rows=silver_supplier_after,
    )
    silver_category_ref_metrics = build_domain_entity_metrics(
        accepted_rows=silver_category_ref_accepted,
        rejected_rows=silver_category_ref_rejected,
        deduplicated_rows=silver_category_ref_deduplicated,
        before_scope_rows=silver_category_ref_before,
        after_scope_rows=silver_category_ref_after,
    )
    silver_purchase_order_metrics = build_domain_entity_metrics(
        accepted_rows=silver_purchase_order_accepted,
        rejected_rows=silver_purchase_order_rejected,
        deduplicated_rows=silver_purchase_order_deduplicated,
        before_scope_rows=silver_purchase_order_before,
        after_scope_rows=silver_purchase_order_after,
    )
    silver_purchase_order_line_metrics = build_domain_entity_metrics(
        accepted_rows=silver_purchase_order_line_accepted,
        rejected_rows=silver_purchase_order_line_rejected,
        deduplicated_rows=silver_purchase_order_line_deduplicated,
        before_scope_rows=silver_purchase_order_line_before,
        after_scope_rows=silver_purchase_order_line_after,
    )
    silver_notice_purchase_order_link_metrics = build_domain_entity_metrics(
        accepted_rows=silver_notice_purchase_order_link_accepted,
        rejected_rows=silver_notice_purchase_order_link_rejected,
        deduplicated_rows=silver_notice_purchase_order_link_deduplicated,
        before_scope_rows=silver_notice_purchase_order_link_before,
        after_scope_rows=silver_notice_purchase_order_link_after,
    )
    silver_purchase_order_line_text_ann_metrics = build_domain_entity_metrics(
        accepted_rows=silver_purchase_order_line_text_ann_accepted,
        rejected_rows=silver_purchase_order_line_text_ann_rejected,
        deduplicated_rows=silver_purchase_order_line_text_ann_deduplicated,
        before_scope_rows=silver_purchase_order_line_text_ann_before,
        after_scope_rows=silver_purchase_order_line_text_ann_after,
    )

    progress_write(
        "[normalized] ordenes_compra summary: "
        f"processed={processed:,}, "
        "header{"
        f"accepted={ordenes_metrics['accepted_rows']:,} "
        f"deduplicated={ordenes_metrics['deduplicated_rows']:,} "
        f"inserted_delta={ordenes_metrics['inserted_delta_rows']:,} "
        f"existing_or_updated={ordenes_metrics['existing_or_updated_rows']:,} "
        f"rejected={ordenes_metrics['rejected_rows']:,}"
        "} "
        "items{"
        f"accepted={ordenes_items_metrics['accepted_rows']:,} "
        f"deduplicated={ordenes_items_metrics['deduplicated_rows']:,} "
        f"inserted_delta={ordenes_items_metrics['inserted_delta_rows']:,} "
        f"existing_or_updated={ordenes_items_metrics['existing_or_updated_rows']:,} "
        f"rejected={ordenes_items_metrics['rejected_rows']:,}"
        "} "
        "buyers{"
        f"accepted={buyers_metrics['accepted_rows']:,} "
        f"deduplicated={buyers_metrics['deduplicated_rows']:,} "
        f"inserted_delta={buyers_metrics['inserted_delta_rows']:,} "
        f"existing_or_updated={buyers_metrics['existing_or_updated_rows']:,} "
        f"rejected={buyers_metrics['rejected_rows']:,}"
        "} "
        "suppliers{"
        f"accepted={suppliers_metrics['accepted_rows']:,} "
        f"deduplicated={suppliers_metrics['deduplicated_rows']:,} "
        f"inserted_delta={suppliers_metrics['inserted_delta_rows']:,} "
        f"existing_or_updated={suppliers_metrics['existing_or_updated_rows']:,} "
        f"rejected={suppliers_metrics['rejected_rows']:,}"
        "} "
        "categories{"
        f"accepted={categories_metrics['accepted_rows']:,} "
        f"deduplicated={categories_metrics['deduplicated_rows']:,} "
        f"inserted_delta={categories_metrics['inserted_delta_rows']:,} "
        f"existing_or_updated={categories_metrics['existing_or_updated_rows']:,} "
        f"rejected={categories_metrics['rejected_rows']:,}"
        "} "
        "silver_core{"
        f"purchase_order_deduplicated={silver_purchase_order_metrics['deduplicated_rows']:,} "
        f"purchase_order_line_deduplicated={silver_purchase_order_line_metrics['deduplicated_rows']:,}"
        "} "
        "silver_dims{"
        f"org_deduplicated={silver_buying_org_metrics['deduplicated_rows']:,} "
        f"unit_deduplicated={silver_contracting_unit_metrics['deduplicated_rows']:,} "
        f"supplier_deduplicated={silver_supplier_metrics['deduplicated_rows']:,} "
        f"category_deduplicated={silver_category_ref_metrics['deduplicated_rows']:,}"
        "} "
        "silver_links{"
        f"notice_purchase_order_link_deduplicated={silver_notice_purchase_order_link_metrics['deduplicated_rows']:,}"
        "} "
        "annotations{"
        f"purchase_order_line_text_ann_deduplicated={silver_purchase_order_line_text_ann_metrics['deduplicated_rows']:,}"
        "}",
        enabled=show_progress,
    )
    progress_write("[normalized] ordenes_compra done", enabled=show_progress)
    if on_checkpoint is not None:
        on_checkpoint(last_id, processed)
    return {
        "processed_rows": processed,
        "last_raw_id": last_id,
        "entity_metrics": {
            "ordenes_compra": ordenes_metrics,
            "ordenes_compra_items": ordenes_items_metrics,
            "buyers": buyers_metrics,
            "suppliers": suppliers_metrics,
            "categories": categories_metrics,
            "silver_buying_org": silver_buying_org_metrics,
            "silver_contracting_unit": silver_contracting_unit_metrics,
            "silver_supplier": silver_supplier_metrics,
            "silver_category_ref": silver_category_ref_metrics,
            "silver_purchase_order": silver_purchase_order_metrics,
            "silver_purchase_order_line": silver_purchase_order_line_metrics,
            "silver_notice_purchase_order_link": silver_notice_purchase_order_link_metrics,
            "silver_purchase_order_line_text_ann": silver_purchase_order_line_text_ann_metrics,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build normalized tables from raw datasets")
    parser.add_argument(
        "--dataset",
        choices=["all", "licitacion", "orden_compra"],
        default="all",
        help="Dataset to process",
    )
    parser.add_argument(
        "--source-file-id",
        default=None,
        help="Optional source_file_id scope for bounded processing",
    )
    parser.add_argument("--fetch-size", type=int, default=10_000, help="Rows fetched per page")
    parser.add_argument("--chunk-size", type=int, default=500, help="Rows per upsert chunk")
    parser.add_argument(
        "--limit-rows",
        type=int,
        default=0,
        help="Limit raw rows processed per dataset (0 means all)",
    )
    parser.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable progress bars and timed stage logs (default: true)",
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resume/skip completed dataset phases using state file (default: true)",
    )
    parser.add_argument(
        "--incremental",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Process only new raw rows (id > last_processed_raw_id) per dataset "
            "(default: true)"
        ),
    )
    parser.add_argument(
        "--state-path",
        default="data/runtime/normalized_build_state.json",
        help="State file path for resumable dataset phases",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Clear existing normalized state file before processing",
    )
    parser.add_argument(
        "--debug-telemetry",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Emit additional checkpoint telemetry details (default: false)",
    )
    parser.add_argument(
        "--state-checkpoint-every-pages",
        type=int,
        default=1,
        help=(
            "Persist resumable state every N committed fetch pages "
            "(default: 1, checkpoint after every commit)"
        ),
    )
    parser.add_argument(
        "--quality-preflight",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run a dataset preflight quality audit before processing (default: true)",
    )
    parser.add_argument(
        "--quality-preflight-fail-fast",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Fail before processing when preflight max issue rate exceeds threshold "
            "(default: false)"
        ),
    )
    parser.add_argument(
        "--quality-gate-checkpoint-every-pages",
        type=int,
        default=QUALITY_GATE_CHECKPOINT_EVERY_PAGES_DEFAULT,
        help=(
            "Evaluate quality gate every N committed pages during processing "
            f"(default: {QUALITY_GATE_CHECKPOINT_EVERY_PAGES_DEFAULT})"
        ),
    )
    parser.add_argument(
        "--quality-gate-fail-fast",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Fail early during processing when checkpoint quality gate fails "
            "(default: true)"
        ),
    )
    parser.add_argument(
        "--quality-gate-min-rows-before-fail-fast",
        type=int,
        default=QUALITY_GATE_MIN_ROWS_BEFORE_FAIL_FAST_DEFAULT,
        help=(
            "Minimum processed raw rows before quality checkpoint fail-fast is enforced "
            f"(default: {QUALITY_GATE_MIN_ROWS_BEFORE_FAIL_FAST_DEFAULT})"
        ),
    )
    args = parser.parse_args()
    if args.fetch_size <= 0:
        raise ValueError("--fetch-size must be > 0")
    if args.chunk_size <= 0:
        raise ValueError("--chunk-size must be > 0")
    if args.limit_rows < 0:
        raise ValueError("--limit-rows must be >= 0")
    if args.state_checkpoint_every_pages <= 0:
        raise ValueError("--state-checkpoint-every-pages must be > 0")
    if args.quality_gate_checkpoint_every_pages <= 0:
        raise ValueError("--quality-gate-checkpoint-every-pages must be > 0")
    if args.quality_gate_min_rows_before_fail_fast < 0:
        raise ValueError("--quality-gate-min-rows-before-fail-fast must be >= 0")
    if args.chunk_size > 5000:
        progress_write(
            "[normalized] warning: large chunk-size may increase statement failures; consider <= 1000",
            enabled=args.progress,
        )

    state_path = Path(args.state_path).expanduser().resolve()
    if args.reset_state and state_path.exists():
        state_path.unlink()
    state = load_state(state_path)

    datasets: list[str]
    if args.dataset == "all":
        datasets = ["licitacion", "orden_compra"]
    else:
        datasets = [args.dataset]

    with SessionLocal() as session:
        for dataset in datasets:
            dataset_state = state.get(dataset)
            if not isinstance(dataset_state, dict):
                dataset_state = {}
            snapshot = raw_snapshot(session, dataset, source_file_id=args.source_file_id)
            if args.resume and should_skip_dataset(state, dataset, snapshot):
                progress_write(
                    f"[normalized] skip {dataset}: source snapshot unchanged and dataset already completed",
                    enabled=args.progress,
                )
                continue

            start_after_id = resolve_start_after_id(dataset_state, incremental=args.incremental)
            last_processed_checkpoint_before_run = max(
                0,
                state_int(dataset_state.get("last_processed_raw_id"), 0),
            )
            mode_label = "incremental" if args.incremental else "full"
            if args.source_file_id:
                mode_label = f"{mode_label}_source_file_scope"
            progress_write(
                f"[normalized] dataset={dataset} mode={mode_label} start_after_id={start_after_id:,}",
                enabled=args.progress,
            )
            if args.quality_preflight:
                preflight_audit = run_dataset_preflight_quality_audit(
                    session,
                    dataset=dataset,
                    start_after_id=start_after_id,
                    limit_rows=args.limit_rows,
                    source_file_id=args.source_file_id,
                )
                progress_write(
                    format_preflight_quality_audit(preflight_audit),
                    enabled=args.progress,
                )
                if (
                    args.quality_preflight_fail_fast
                    and float(preflight_audit.get("max_rate") or 0.0) > QUALITY_GATE_MAX_ERROR_RATE
                ):
                    progress_write(
                        "[normalized] preflight fail-fast: max issue rate exceeds quality threshold",
                        enabled=args.progress,
                    )
                    return 1

            state[dataset] = {
                "status": "running",
                "source_total_rows": snapshot["total_rows"],
                "source_max_id": snapshot["max_id"],
                "mode": mode_label,
                "start_after_id": start_after_id,
                "last_processed_raw_id": start_after_id,
                "processed_rows_current_run": 0,
            }
            save_state(state_path, state)
            run: PipelineRun | None = None
            step: PipelineRunStep | None = None

            def persist_checkpoint(last_raw_id: int, processed_rows: int) -> None:
                current = state.get(dataset)
                if not isinstance(current, dict):
                    return
                current["last_processed_raw_id"] = max(
                    state_int(current.get("last_processed_raw_id"), 0),
                    max(0, last_raw_id),
                )
                current["processed_rows_current_run"] = processed_rows
                save_state(state_path, state)

            def evaluate_quality_checkpoint(
                last_raw_id: int,
                processed_rows: int,
                entity_metrics: dict[str, dict[str, Any]],
            ) -> None:
                quality_issues = collect_normalized_quality_issues(
                    cast(dict[str, dict[str, int]], entity_metrics)
                )
                quality_gate = evaluate_normalized_quality_gate(
                    cast(dict[str, dict[str, int]], entity_metrics),
                    quality_issues,
                )
                decision = str(quality_gate.get("decision"))
                dataset_error_rate = float(
                    quality_gate.get("dataset_metrics", {}).get("error_rate") or 0.0
                )
                if args.debug_telemetry:
                    progress_write(
                        "[normalized][debug] quality checkpoint: "
                        f"dataset={dataset} raw_id={last_raw_id:,} processed={processed_rows:,} "
                        f"decision={decision} error_rate={dataset_error_rate:.4%}",
                        enabled=args.progress,
                    )
                if not args.quality_gate_fail_fast:
                    return
                if processed_rows < args.quality_gate_min_rows_before_fail_fast:
                    return
                if decision != "failed":
                    return
                reason = str(quality_gate.get("decision_reason") or "unknown_reason")
                raise RuntimeError(
                    "normalized quality checkpoint failed early: "
                    f"{reason} (dataset={dataset}, raw_id={last_raw_id}, "
                    f"processed_rows={processed_rows}, error_rate={dataset_error_rate:.4%})"
                )

            try:
                stale_runs_closed = close_stale_running_runs(session, dataset=dataset)
                if stale_runs_closed > 0:
                    progress_write(
                        f"[normalized] closed stale running runs: dataset={dataset} count={stale_runs_closed}",
                        enabled=args.progress,
                    )
                run, step = create_normalized_run(session, dataset, mode_label)
                session.commit()
                with timed_step(f"normalized dataset={dataset}", enabled=args.progress):
                    if dataset == "licitacion":
                        metrics = process_licitaciones(
                            session=session,
                            fetch_size=args.fetch_size,
                            chunk_size=args.chunk_size,
                            limit_rows=args.limit_rows,
                            show_progress=args.progress,
                            start_after_id=start_after_id,
                            source_file_id=args.source_file_id,
                            debug_telemetry=args.debug_telemetry,
                            state_checkpoint_every_pages=args.state_checkpoint_every_pages,
                            on_checkpoint=persist_checkpoint,
                            on_quality_checkpoint=evaluate_quality_checkpoint,
                            quality_gate_checkpoint_every_pages=args.quality_gate_checkpoint_every_pages,
                        )
                    else:
                        metrics = process_ordenes_compra(
                            session=session,
                            fetch_size=args.fetch_size,
                            chunk_size=args.chunk_size,
                            limit_rows=args.limit_rows,
                            show_progress=args.progress,
                            start_after_id=start_after_id,
                            source_file_id=args.source_file_id,
                            debug_telemetry=args.debug_telemetry,
                            state_checkpoint_every_pages=args.state_checkpoint_every_pages,
                            on_checkpoint=persist_checkpoint,
                            on_quality_checkpoint=evaluate_quality_checkpoint,
                            quality_gate_checkpoint_every_pages=args.quality_gate_checkpoint_every_pages,
                        )

                last_processed_raw_id = max(
                    state_int(metrics.get("last_raw_id"), start_after_id),
                    start_after_id,
                )
                entity_metrics = cast(
                    dict[str, dict[str, int]],
                    metrics.get("entity_metrics", {}),
                )
                quality_issues = collect_normalized_quality_issues(entity_metrics)
                persist_normalized_quality_issues(session, run.id, dataset, quality_issues)
                quality_gate = evaluate_normalized_quality_gate(entity_metrics, quality_issues)
                decision = str(quality_gate.get("decision"))

                if decision == "failed":
                    last_processed_raw_id = last_processed_checkpoint_before_run
                    error_summary = (
                        "normalized quality gate failed: "
                        f"{quality_gate.get('decision_reason', 'unknown_reason')}"
                    )
                    mark_normalized_run_failed(
                        run=run,
                        step=step,
                        error_summary=error_summary,
                        quality_gate=quality_gate,
                    )
                    state[dataset] = {
                        "status": "failed",
                        "source_total_rows": snapshot["total_rows"],
                        "source_max_id": snapshot["max_id"],
                        "mode": mode_label,
                        "start_after_id": start_after_id,
                        "processed_rows_last_run": metrics["processed_rows"],
                        "processed_rows_current_run": metrics["processed_rows"],
                        "processed_rows_total": state_int(dataset_state.get("processed_rows_total"), 0)
                        + state_int(metrics.get("processed_rows"), 0),
                        "last_processed_raw_id": last_processed_raw_id,
                        "last_raw_id": metrics["last_raw_id"],
                        "quality_gate": quality_gate,
                    }
                    save_state(state_path, state)
                    session.commit()
                    progress_write(
                        f"[normalized] dataset={dataset} failed by quality gate: "
                        f"{quality_gate.get('decision_reason')}",
                        enabled=args.progress,
                    )
                    return 1

                mark_normalized_run_completed(
                    run=run,
                    step=step,
                    processed_rows=state_int(metrics.get("processed_rows"), 0),
                    quality_gate=quality_gate,
                )
                state[dataset] = {
                    "status": "completed",
                    "source_total_rows": snapshot["total_rows"],
                    "source_max_id": snapshot["max_id"],
                    "mode": mode_label,
                    "start_after_id": start_after_id,
                    "processed_rows_last_run": metrics["processed_rows"],
                    "processed_rows_current_run": metrics["processed_rows"],
                    "processed_rows_total": state_int(dataset_state.get("processed_rows_total"), 0)
                    + state_int(metrics.get("processed_rows"), 0),
                    "last_processed_raw_id": last_processed_raw_id,
                    "last_raw_id": metrics["last_raw_id"],
                    "quality_gate": quality_gate,
                }
                save_state(state_path, state)
                session.commit()
            except Exception as exc:
                persist_failed_dataset_state(
                    session=session,
                    state=state,
                    dataset=dataset,
                    snapshot=snapshot,
                    state_path=state_path,
                )
                if run is not None and step is not None:
                    mark_normalized_run_failed(
                        run=run,
                        step=step,
                        error_summary=str(exc),
                    )
                    session.commit()
                raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

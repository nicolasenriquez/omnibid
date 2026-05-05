from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from backend.models.operational import DataQualityIssue

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


def _state_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def collect_normalized_quality_issues(
    entity_metrics: dict[str, dict[str, int]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for entity_name, metrics in entity_metrics.items():
        processed_rows = max(0, _state_int(metrics.get("processed_rows"), 0))
        rejected_rows = max(0, _state_int(metrics.get("rejected_rows"), 0))
        if rejected_rows <= 0:
            continue
        error_rate = (rejected_rows / processed_rows) if processed_rows > 0 else 0.0
        is_domain_identity_issue = entity_name in QUALITY_GATE_DOMAIN_IDENTITY_FIELDS
        identity_field = str(
            metrics.get("identity_field")
            or QUALITY_GATE_DOMAIN_IDENTITY_FIELDS.get(entity_name, "")
        )
        default_rejection_reason = (
            "missing_identity" if is_domain_identity_issue else "rejected_rows"
        )
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
    source_file_id: Any | None = None,
) -> None:
    for issue in issues:
        quality_issue = DataQualityIssue(
            run_id=run_id,
            source_file_id=source_file_id,
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
        max(0, _state_int(metrics.get("processed_rows"), 0))
        for metrics in entity_metrics.values()
    )
    total_rejected_rows = sum(
        max(0, _state_int(metrics.get("rejected_rows"), 0))
        for metrics in entity_metrics.values()
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

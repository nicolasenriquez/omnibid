# Data Architecture

## Layer Intent

## Raw
Raw source ingestion with lineage and source metadata.

## Silver (Normalized implementation)
Deterministic canonicalization and relational domain contracts.

## Gold
Business-ready aggregates and predictive/decision outputs (deferred until Silver maturity gates pass).

## Current Implemented Silver Baseline

Implemented normalized entities:
- `normalized_licitaciones`
- `normalized_licitacion_items`
- `normalized_ofertas`
- `normalized_ordenes_compra`
- `normalized_ordenes_compra_items`
- `normalized_buyers`
- `normalized_suppliers`
- `normalized_categories`

Current canonical identity contracts:
- buyer key: `buyer_key` (`CodigoUnidadCompra`)
- supplier key: `supplier_key` precedence `codigo:<CodigoProveedor>` then `rut:<RutProveedor>`
- category key: `category_key` (`codigoCategoria`)

## Current Implemented Silver Procurement-Cycle Layer

Silver procurement-cycle canonical path:
- notice -> notice line -> bid submission -> award outcome -> purchase order -> purchase order line

Implemented canonical entities:
- `silver_notice`
- `silver_notice_line`
- `silver_bid_submission`
- `silver_award_outcome`
- `silver_purchase_order`
- `silver_purchase_order_line`
- `silver_buying_org`
- `silver_contracting_unit`
- `silver_supplier`
- `silver_category_ref`
- `silver_notice_purchase_order_link`
- `silver_supplier_participation`

Implemented semantic annotation entities:
- `silver_notice_text_ann`
- `silver_notice_line_text_ann`
- `silver_purchase_order_line_text_ann`

Boundary rules (enforced):
- Silver includes deterministic enrichments and versioned semantic annotations.
- Silver excludes predictive business outputs (opportunity/win scores, forecasts, anomaly verdicts).
- Silver annotation contract stores TF-IDF references only (`tfidf_artifact_ref`), not serialized vectors.

## Next Stage (Gold)

- business aggregates, predictive outputs, and decision-support scoring move to Gold/feature-serving layers
- leakage-sensitive model features are blocked from Silver persistence

Reference artifacts:
- `openspec/changes/expand-silver-procurement-cycle-and-feature-foundation-2026-04-22/`
- `docs/evidence/silver_procurement_cycle_grain_baseline_2026-04-22.md`
- `docs/evidence/silver_procurement_cycle_validation_2026-04-23.md`

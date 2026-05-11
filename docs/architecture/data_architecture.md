# Data Architecture

## Layer Intent

## Raw
Raw source ingestion with lineage and source metadata.

The Mercado Publico API operational lane is documented in `docs/architecture/external_api_ingestion.md` and maps to the operational tables listed in `docs/architecture/data_model.md`.

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

## Read-Only Procurement Investigation Workspace

The first Gold-facing slice is a read-only procurement investigation workspace over the implemented Silver procurement-cycle layer.

Scope:
- one investigation summary per `notice_id + item_code`
- tabular offer evidence before narrative context
- tabular purchase-order-line evidence with explicit match reason and certainty
- bounded context JSON for analyst/agent workflows
- table and kanban-style UI states backed by the same API contract

Boundary rules:
- Silver remains canonical source facts and deterministic annotations.
- Gold investigation models may express certainty, workflow state, and agent handoff context.
- Agent narrative must not be persisted as canonical business truth.
- ONU-only purchase-order-line matching is plausible evidence, not conclusive evidence.

Reference artifacts:
- `openspec/changes/expand-silver-procurement-cycle-and-feature-foundation-2026-04-22/`
- `docs/evidence/silver_procurement_cycle_grain_baseline_2026-04-22.md`
- `docs/evidence/silver_procurement_cycle_validation_2026-04-23.md`
- `openspec/changes/gold-procurement-investigation-workspace/`
- `docs/evidence/procurement_investigation_workspace_join_profile_2026-04-28.md`
- `docs/evidence/procurement_investigation_workspace_validation_2026-04-28.md`

## Opportunity Workspace Read Model

The Opportunity Workspace MVP is a UI and read-API over existing procurement-cycle facts.

Canonical UI grain:
- Radar: one card per licitación/notice.
- Explorer: one parent row per licitación/notice.
- Detail: one notice header with child products/services, offers, awards, purchase orders, and relationship evidence.

Default source strategy:
- use `silver_notice` as the parent opportunity source.
- use `silver_notice_line`, `silver_bid_submission`, `silver_award_outcome`, `silver_purchase_order`, and `silver_purchase_order_line` for child evidence.
- use documented Normalized joins only for display fields currently absent from Silver, such as buyer display and region.
- list/summary/detail queries must coalesce parent display/stage fields from `normalized_licitaciones` when `silver_notice` values are null (`title`, `official_status`, `estimated_amount`, `publication_date`, `close_date`).
- keep frontend read-only behavior unchanged: missing values remain explicitly unavailable when neither Silver nor Normalized has data.

Boundary rules:
- list and Kanban endpoints must not join child rows in a way that duplicates parent opportunities.
- parent totals must distinguish notice-level values from child-level evidence.
- relationship certainty is required where purchase-order-line matching is approximate.
- predictive business outputs remain outside Silver and outside the read-only MVP.

Implemented API/UI paths:
- backend read API: `backend/api/routers/opportunities.py`
- frontend route: `client/app/licitaciones/page.tsx`
- frontend feature module: `client/src/features/opportunity-workspace/`
- API client/types: `client/src/lib/api/`, `client/src/types/`

Agent guidance:
- keep list/summary endpoints at notice grain.
- move line, offer, award, and purchase-order evidence into detail contracts unless a documented product requirement changes list grain.
- keep UI labels Spanish; keep backend DTO fields stable and typed.

## Mercado Publico API Read-Model Propagation

Current daily API propagation contract:
- rolling discovery snapshots are persisted first (`mercado_publico_notice_snapshot`)
- selective `detail-by-codigo` runs next (missing/stale detail candidates)
- persisted API payloads are canonicalized into existing Normalized + Silver entities
- Silver postprocess refreshes derived counts/flags for notice and line surfaces
- the lane is additive/backend-only: it hardens upstream ingestion and read-model propagation without mutating frontend contracts.
- Explorer parent-field completeness depends on this propagation lane; if detail enrichment is skipped, open notices can remain sparse by design.

Merge semantics:
- canonical upserts are complete-only: non-null existing values are preserved against null/blank incoming payload fields
- detail payload rows are applied after rolling rows so richer fields take precedence for the same business keys

# Data Model

## Implemented Baseline (Current)

## Operational
- `source_files`
- `pipeline_runs`
- `pipeline_run_steps`
- `ingestion_batches`
- `data_quality_issues`

## External API Ingestion Operational Tables
- `api_source_request`
- `api_source_payload`
- `mercado_publico_notice_snapshot`

These tables preserve request, payload, and snapshot lineage for the Mercado Publico notice-sync lane.
Daily sync+Silver runs also register a logical API snapshot artifact in `source_files` with `dataset_type=mercado_publico_api_notice` so downstream `source_file_id` contracts remain explicit.
The daily read-model propagation DAG then materializes API payload rows into existing `normalized_*` and `silver_*` tables (not a parallel schema) and records ordered pipeline steps:
- `mp_api_rolling_refresh`
- `mp_api_detail_enrichment`
- `mp_api_payload_canonicalization`
- `mp_api_silver_postprocess`
See `docs/architecture/external_api_ingestion.md` for the API lane runtime contract and `docs/architecture/system_architecture.md` for operator/runtime boundaries.

## Raw
- `raw_licitaciones`
- `raw_ordenes_compra`

## Silver (Normalized implementation)
- `normalized_licitaciones`
- `normalized_licitacion_items`
- `normalized_ofertas`
- `normalized_ordenes_compra`
- `normalized_ordenes_compra_items`
- `normalized_buyers`
- `normalized_suppliers`
- `normalized_categories`

## Silver Procurement-Cycle Canonical (Implemented)

Core process entities:
- `silver_notice`
- `silver_notice_line`
- `silver_bid_submission`
- `silver_award_outcome`
- `silver_purchase_order`
- `silver_purchase_order_line`

Master entities:
- `silver_buying_org`
- `silver_contracting_unit`
- `silver_supplier`
- `silver_category_ref`

Bridge/fact entities:
- `silver_notice_purchase_order_link`
- `silver_supplier_participation`

Semantic annotation entities:
- `silver_notice_text_ann`
- `silver_notice_line_text_ann`
- `silver_purchase_order_line_text_ann`

Deterministic enrichment fields are implemented in Silver notice/line/purchase-order entities, including:
- temporal chain durations
- administrative flags
- structural/competition metrics
- notice-to-order materialization metrics

Annotation contract highlights:
- explicit `nlp_version`
- annotation metadata only (tokens/tags/ngrams)
- `tfidf_artifact_ref` reference strings only (`tfidf://...`)
- no serialized vectors and no business prediction scores in Silver

## Current Read Models

Documented read-only API models sit on top of Silver and documented Normalized display joins:

- opportunity list/summary/detail contracts under `/opportunities`
- procurement line investigation list/detail contracts under `/investigations/procurement-lines`
- frontend view models under `client/src/features/opportunity-workspace/`

These are read contracts, not canonical persisted business facts. Keep canonical facts in Raw/Normalized/Silver tables and add persisted Gold tables only when evidence shows the read contract needs materialization.

## Gold Investigation Read Models

Initial Gold investigation contracts:
- `gold_procurement_line_investigation`: one row per `notice_id + item_code`
- `gold_procurement_line_offer_evidence`: one row per line offer evidence item
- `gold_procurement_line_purchase_evidence`: one row per plausible purchase-order-line relationship
- `gold_procurement_line_context`: bounded JSON context for detail and agent handoff

Current implementation starts as a read-only API/query contract. Persisted Gold tables or views should be introduced only after join cardinality and performance evidence justify persistence.

Certainty contract:
- `high`: reserved for direct consistent evidence beyond ONU-only matching
- `medium`: limited ambiguity with compatible notice and product evidence
- `low`: indirect or broad ambiguous evidence, including many ONU-based candidates
- `none`: no purchase-order-line evidence

For detailed scope, constraints, implementation status, and milestones:
- `openspec/changes/expand-silver-procurement-cycle-and-feature-foundation-2026-04-22/`
- `docs/runbooks/silver_procurement_cycle_implementation_plan.md`
- `openspec/changes/gold-procurement-investigation-workspace/`
- `docs/runbooks/procurement_investigation_workspace_plan.md`

## Next Target

- stabilize Opportunity Workspace read API/frontend behavior
- add persisted Gold aggregates or feature-serving outputs only after a new OpenSpec change and validation evidence
- keep predictive scoring and model outputs in downstream layers only

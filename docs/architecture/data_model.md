# Data Model

## Implemented Baseline (Current)

## Operational
- `source_files`
- `pipeline_runs`
- `pipeline_run_steps`
- `ingestion_batches`
- `data_quality_issues`

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

## Next Target (Post-Silver)

- Gold aggregates and feature-serving outputs (outside Silver scope)
- predictive scoring and model outputs in downstream layers only

For detailed scope, constraints, implementation status, and milestones:
- `openspec/changes/expand-silver-procurement-cycle-and-feature-foundation-2026-04-22/`
- `docs/runbooks/silver_procurement_cycle_implementation_plan.md`

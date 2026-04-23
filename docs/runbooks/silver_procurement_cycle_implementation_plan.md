# Silver Procurement Cycle Implementation Plan

Date: 2026-04-22
Status: Implementation-aligned (Tasks 1-6 executed for current change scope)

## Objective

Deliver the next Silver stage as a canonical procurement-cycle model with deterministic feature foundations, while preserving fail-fast lineage and stage-gated quality discipline.

## Current Implementation State

Completed in current scope:
- canonical Silver procurement-cycle entities (core + master + bridge)
- deterministic enrichment columns and refresh logic
- leakage guardrails for forbidden predictive/future-prefixed Silver fields
- versioned semantic annotation entities for notice, notice-line, and purchase-order-line text
- annotation contract checks (`tfidf_artifact_ref` references only, no serialized vectors)

Validated evidence:
- `docs/evidence/silver_procurement_cycle_validation_2026-04-23.md`

## Scope Boundary

In scope:
- canonical process entities
- canonical master entities
- explicit bridge entities
- deterministic enrichments
- versioned semantic annotation tables

Out of scope:
- Gold aggregates
- business prediction scores
- recommendation/ranking outputs

## Milestones

## M0 - Contract and Baseline Freeze

Deliverables:
- grain evidence validated and documented
- canonical entity grain definitions approved
- deterministic identity and FK contracts approved

Acceptance:
- evidence file exists and is review-approved
- OpenSpec proposal/design/spec/tasks approved

Suggested issue slices:
1. "Freeze Silver procurement entity grain contracts"
2. "Document canonical identity precedence and optional-link policy"

## M1 - Core Procurement Cycle Entities

Deliverables:
- additive schema/model contracts for:
  - notices
  - notice lines
  - bid submissions
  - award outcomes
  - purchase orders
  - purchase-order lines

Acceptance:
- migration/ORM parity checks pass
- deterministic replay tests pass for core entities

Suggested issue slices:
1. "Add core procurement-cycle schema and model contracts"
2. "Add core entity grain integrity tests"
3. "Integrate core builders into normalized pipeline"

## M2 - Master and Bridge Entities

Deliverables:
- master entities:
  - buying organizations
  - contracting units
  - supplier registry
  - category reference
- bridges:
  - notice-purchase-order links
  - supplier participation facts

Acceptance:
- FK integrity and cardinality tests pass
- optional notice linkage behavior validated on controlled sample

Suggested issue slices:
1. "Add master-domain entities and key contracts"
2. "Add explicit notice-PO and supplier-participation bridges"
3. "Validate optional-link semantics and bridge cardinality"

## M3 - Deterministic Enrichment Layer

Deliverables:
- text normalization fields (`*_raw`, `*_clean`)
- temporal durations and chain flags
- administrative/contract flags
- structural and competition metrics
- notice-to-order materialization metrics

Acceptance:
- derivation tests are deterministic and replay-stable
- leakage guardrails block future-dependent features

Derivation formula catalog (deterministic):
- `days_publication_to_close = close_date - publication_date` (days, nullable if chain missing)
- `days_creation_to_close = close_date - created_date` (days, nullable if chain missing)
- `days_close_to_award = award_date - close_date` (days, nullable if chain missing)
- `has_missing_date_chain_flag = any(publication_date, close_date, award_date is null)`
- `notice_line_count = count(silver_notice_line where notice_id)`
- `notice_bid_count = count(silver_bid_submission where notice_id)`
- `notice_supplier_count = count(distinct supplier_key in silver_bid_submission where notice_id)`
- `notice_selected_bid_count = count(silver_bid_submission where notice_id and selected_offer_flag=true)`
- `notice_awarded_line_count = count(silver_award_outcome where notice_id and (selected_offer_flag=true or awarded_line_amount is not null))`
- `notice_purchase_order_count = count(silver_notice_purchase_order_link where notice_id)`
- `notice_has_purchase_order_flag = notice_purchase_order_count > 0`
- `notice_awarded_to_order_conversion_flag = notice_awarded_line_count > 0 and notice_purchase_order_count > 0`
- `line_bid_count = count(silver_bid_submission where notice_id + item_code)`
- `line_supplier_count = count(distinct supplier_key in silver_bid_submission where notice_id + item_code)`
- `line_min_offer_amount = min(total_price_offered where notice_id + item_code)`
- `line_max_offer_amount = max(total_price_offered where notice_id + item_code)`
- `line_avg_offer_amount = avg(total_price_offered where notice_id + item_code)`
- `line_median_offer_amount = percentile_cont(0.5) over total_price_offered where notice_id + item_code`
- `line_price_dispersion_ratio = (line_max_offer_amount - line_min_offer_amount) / line_avg_offer_amount` when denominator is non-zero
- `days_order_creation_to_acceptance = order_accepted_at - order_created_at` (days, nullable if chain missing)
- `days_order_creation_to_cancellation = order_cancelled_at - order_created_at` (days, nullable if chain missing)
- `purchase_order_line_count = count(silver_purchase_order_line where purchase_order_id)`
- `purchase_order_total_quantity = sum(quantity_ordered where purchase_order_id)`
- `purchase_order_total_net_amount = sum(line_net_total where purchase_order_id)`
- `purchase_order_unique_product_count = count(distinct onu_product_code where purchase_order_id)`

Suggested issue slices:
1. "Add temporal and administrative deterministic derivations"
2. "Add structural and competition metric derivations"
3. "Add leakage guardrails for Silver feature columns"

## M4 - Semantic Annotations and Feature Handoff

Deliverables:
- versioned annotation entities:
  - notice text annotations
  - notice-line text annotations
  - purchase-order-line text annotations
- deterministic NLP feature extraction implementation using sklearn text vectorizers:
  - token normalization and n-grams (`CountVectorizer`)
  - TF-IDF artifact generation (`TfidfVectorizer`) with reference-only persistence
- annotation policy docs (annotation-only, no business scoring)
- feature handoff contract for downstream Gold/ML

Acceptance:
- annotation tables include version/artifact refs
- no supervised model training or prediction persistence in Silver NLP jobs
- docs clearly separate Silver annotation outputs vs Gold/ML outputs

Annotation policy and validation checks:
- annotation entities accept technical metadata only (tokens/tags/ngrams/artifact refs)
- `tfidf_artifact_ref` must be a reference string (`tfidf://...`)
- serialized TF-IDF vectors are forbidden in Silver tables
- predictive fields (`*_score`, `*_probability`, `future_*`) are blocked by Silver guardrails

Suggested issue slices:
1. "Add versioned semantic annotation schemas"
2. "Implement deterministic sklearn-based text feature extraction (no training)"
3. "Add deterministic annotation write/read tests"
4. "Publish Silver-to-Gold feature handoff contract"

## Quality Gates per Milestone

- `just quality`
- targeted unit tests for each added entity/derivation
- controlled `pipeline-normalized` validation run
- evidence capture under `docs/evidence/`

## Migration Playbook

Apply migrations in order:
1. `202604230010_silver_core`
2. `202604230020_silver_master`
3. `202604230030_silver_enrichment`
4. `202604230040_silver_text_ann`

Operational notes:
- revision IDs must remain within `alembic_version.version_num` (`VARCHAR(32)`)
- run `just db-bootstrap` after migration changes
- run controlled validation slices:
  1. `--dataset licitacion --limit-rows 50`
  2. `--dataset orden_compra --limit-rows 50`

## Approval Checklist

- [ ] Architecture docs updated ("current vs target")
- [ ] OpenSpec artifacts approved
- [ ] Data lineage and fail-fast behavior preserved
- [ ] Explicit confirmation that no predictive scores are persisted in Silver

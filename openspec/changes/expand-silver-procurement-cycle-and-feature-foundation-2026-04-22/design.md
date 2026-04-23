## Context

The repository completed:
- reliability hardening and quality gates
- telemetry reconciliation
- canonical buyer/supplier/category entities in normalized storage

The current normalized layer is robust for ingestion and canonicalization, but domain semantics are still partially embedded in wide tables. The next stage needs to model the procurement process as explicit entities and relationships, while keeping Silver deterministic and non-predictive.

This change defines that target with strict boundaries and phased delivery.

## Goals / Non-Goals

**Goals**
- Model the full procurement lifecycle in Silver as canonical, relational entities.
- Preserve deterministic rebuild and idempotent upsert behavior.
- Keep lineage explicit across all added entities.
- Add reproducible feature-ready enrichments in Silver.
- Introduce versioned semantic annotations in Silver without business scoring outputs.
- Prepare stable contracts for future Gold and feature-store layers.

**Non-Goals**
- Implement Gold business aggregates in this change.
- Implement opportunity scoring, win-probability scoring, forecasting, or anomaly verdict outputs in Silver.
- Introduce feature leakage (future-dependent features at event time).
- Replace Raw contracts or ingestion registration behavior.

## Decisions

1. **Model Silver around procurement process events, not raw export shape.**
   - Canonical process path:
     - notice -> notice line -> bid submission -> award outcome -> purchase order -> purchase order line
   - Rationale: raw CSV rows conflate multiple grains; canonical event entities reduce semantic ambiguity.

2. **Keep notice and purchase-order linkage explicit and optional.**
   - `CodigoLicitacion` in OC is nullable in practice, so notice linkage cannot be required.
   - Rationale: preserving nullable linkage avoids false negatives and invalid forced joins.

3. **Separate offer submissions from award outcomes even when source fields overlap.**
   - `silver_bid_submission` is offer intent/state.
   - `silver_award_outcome` is adjudication result.
   - Rationale: one source row may contain both, but business semantics are different.

4. **Introduce master entities with deterministic keys and explicit precedence.**
   - buying organizations
   - contracting units
   - supplier registry (existing precedence preserved)
   - procurement category reference
   - Rationale: standardized identities reduce downstream join instability.

5. **Add bridge tables where relationships are not 1:1.**
   - `silver_notice_purchase_order_link`
   - `silver_supplier_participation`
   - Rationale: explicit many-to-many bridges keep relationship provenance auditable.

6. **Allow deterministic enrichment in Silver, forbid predictive business outputs.**
   - Allowed:
     - text normalization
     - temporal durations
     - administrative flags
     - structural metrics
     - competition metrics
     - materialization metrics
   - Forbidden:
     - opportunity ranking
     - win probability
     - recommendation scores
     - forecast or anomaly verdict outputs
   - Rationale: preserves Silver as canonical + reproducible derivation layer.

7. **Use versioned semantic annotation side tables in Silver.**
   - notice-level, notice-line-level, purchase-order-line-level annotation contracts
   - include explicit `nlp_version` and artifact references
   - Rationale: enables explainable, repeatable NLP tagging without coupling Silver to model outcomes.

8. **Adopt additive migration strategy with compatibility-first rollout.**
   - Add new canonical entities and FKs incrementally.
   - Keep existing normalized contracts readable during migration window.
   - Rationale: reduces operational risk and avoids disruptive cutovers.

9. **Gate delivery by milestone quality checks before Gold unlock.**
   - each milestone requires parity checks, deterministic replay validation, and telemetry evidence capture
   - Rationale: consistent with repository stage-gated workflow.

10. **Use concise professional `silver_*` physical table names.**
   - Rationale: keep names easy to read and easy to map to business meaning without excessive length.
   - Frozen naming standard:
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
     - `silver_notice_text_ann`
     - `silver_notice_line_text_ann`
     - `silver_purchase_order_line_text_ann`

11. **Persist TF-IDF as artifact references only.**
   - Rationale: artifact references preserve reproducibility and lineage without bloating transactional Silver storage.
   - Contract: no serialized TF-IDF vector snapshots inside Silver tables.

12. **Implement Task 5 NLP with deterministic feature extraction only (no model training in Silver).**
   - Allowed implementation tools:
     - `sklearn.feature_extraction.text.CountVectorizer`
     - `sklearn.feature_extraction.text.TfidfVectorizer`
     - deterministic tokenization/normalization and n-gram extraction
   - Required write contract:
     - persist annotation payload summaries and `tfidf_artifact_ref`
     - persist `nlp_version`, corpus scope metadata, and lineage fields
   - Forbidden in Silver Task 5:
     - `train_test_split` workflows
     - supervised classifier fitting (`fit/predict`) for business outcomes
     - persistence of predicted business scores
   - Rationale: align with MVP notebook tooling while preserving Silver as annotation + feature-foundation stage.

## Proposed Canonical Entities (Target)

Core process entities:
- `silver_notice`
- `silver_notice_line`
- `silver_bid_submission`
- `silver_award_outcome`
- `silver_purchase_order`
- `silver_purchase_order_line`

Master/domain entities:
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

## Risks / Trade-offs

- **[Risk] Wider schema surface increases migration complexity.**
  - Mitigation: additive changes, bounded milestone slices, migration/ORM parity tests.

- **[Risk] Join cardinality mistakes could inflate counts.**
  - Mitigation: enforce grain tests per table and PK/FK contracts before rollout.

- **[Risk] Feature creep could push Gold logic into Silver.**
  - Mitigation: explicit forbidden outputs in spec and quality review checklist.

- **[Risk] NLP annotations may be mistaken as business truth.**
  - Mitigation: require `nlp_version`, artifact reference, and "annotation-only" semantics in schema/docs.

## Migration Plan (Implementation-Oriented)

1. Baseline and contract freeze
   - confirm current grains and linkage sparsity
   - lock table-grain contracts and naming map
2. Core process entities
   - introduce notice/line/bid/award/PO/PO-line contracts with deterministic keys
3. Master entities and bridges
   - complete organizations/units/suppliers/categories + explicit link tables
4. Deterministic enrichment
   - add temporal, structural, competition, and materialization derivations
5. Semantic annotations
   - add versioned annotation tables and deterministic write semantics
   - implement sklearn-based text feature extraction only (count/tfidf/n-grams) with artifact references
   - defer all supervised training/scoring to downstream stages
6. Validation and sign-off
   - replay idempotency, data-quality gates, and architecture/runbook updates

Rollback strategy:
- Keep additive schema slices independently reversible by migration revision.
- Use feature flags / rollout toggles for new builder paths when implemented.
- Preserve prior normalized outputs until each milestone passes validation gates.

## Open Questions

None.

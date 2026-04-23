## Why

The normalized layer is now stable and includes canonical buyers/suppliers/categories, but it still models procurement mostly as wide transactional tables. This constrains analytics quality and delays feature engineering readiness.

Observed source-grain evidence from local CSVs confirms why a stronger Silver contract is needed:
- `202603_lic.csv` (validated on 2026-04-22): `104,844` rows, `5,332` unique notices, `25,300` unique notice-line combinations, and `104,390` unique notice-line-supplier combinations.
- `202604-oc.csv` (validated on 2026-04-22): `208,252` rows, `71,082` unique purchase orders, `208,252` unique purchase-order-line combinations.
- Purchase-order linkage to notices is optional in practice: `72,920` OC rows include `CodigoLicitacion` (`14,618` unique linked notice codes), so hard-required notice linkage is incorrect.

This means the next stage should not be "more cleanup columns." The next stage is a canonical procurement-cycle model plus deterministic feature foundations.

## What Changes

- Expand Silver from transactional normalization to canonical procurement-cycle entities:
  - notice -> notice line -> bid submission -> award outcome -> purchase order -> purchase order line
- Add explicit master entities and bridge contracts:
  - buying organizations, contracting units, supplier registry, procurement category reference
  - explicit optional notice-purchase-order links
  - supplier participation factual bridge
- Define deterministic enrichment boundaries in Silver:
  - text normalization (`*_raw`, `*_clean`)
  - date-duration derivations
  - administrative flags
  - structural and competition metrics
  - procurement materialization metrics
- Define versioned semantic annotation contracts (NLP tags/ngrams/tfidf refs) in Silver without introducing business prediction outputs.
- Establish clear "allowed vs forbidden" feature-engineering behavior in Silver to prevent leakage and Gold overlap.

## Capabilities

### New Capabilities
- `silver-procurement-cycle-domain-model`: Canonical process-oriented Silver entities and relationships for full procurement lifecycle representation.
- `silver-feature-engineering-foundation`: Deterministic, reproducible Silver enrichments and versioned semantic annotations, explicitly separated from predictive scoring.

### Modified Capabilities
- `normalized-domain-entities`: Extended from isolated buyer/supplier/category canonicalization toward a fully connected procurement-cycle model.

## Impact

- Affected future code areas:
  - `backend/models/normalized.py`
  - `backend/normalized/transform.py`
  - `scripts/build_normalized.py`
  - Alembic revisions for additive canonical entities and relationship contracts
  - unit/integration tests for grain contracts, FK integrity, and deterministic metrics
- Operational impact:
  - stronger relational contracts and deterministic feature derivations
  - improved analytics trust and downstream Gold/ML readiness
- Documentation impact:
  - architecture/data model updates
  - implementation milestones and quality gates for staged rollout

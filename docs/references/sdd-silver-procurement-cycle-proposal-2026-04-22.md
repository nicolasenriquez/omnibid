# SDD Note - Silver Procurement Cycle and Feature Foundation Proposal (2026-04-22)

Change: `expand-silver-procurement-cycle-and-feature-foundation-2026-04-22`

## Official Sources Consulted

- PostgreSQL documentation (constraints, FKs, indexes, relational modeling semantics):  
  https://www.postgresql.org/docs/current/
- SQLAlchemy 2.x (ORM relational mapping and deterministic upsert patterns):  
  https://docs.sqlalchemy.org/en/20/
- Alembic operations reference (additive schema migration strategy):  
  https://alembic.sqlalchemy.org/en/latest/ops.html
- scikit-learn text feature extraction docs (vectorizers and deterministic text feature pipelines):
  - https://scikit-learn.org/stable/modules/feature_extraction.html
  - https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html
  - https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.HashingVectorizer.html

## Contextual Domain References (Non-Authoritative for Framework Behavior)

- Procurement analytics notebook pattern reference (event-first staging separation):  
  https://github.com/raestrada/cloud-gob-data-industrial/tree/main/MVP/notebooks
- MVP NLP notebook reference (contains TF-IDF plus supervised-classification example used as pattern input):  
  https://github.com/raestrada/cloud-gob-data-industrial/blob/main/MVP/notebooks/03_nlp_etiquetado.ipynb
- Text mining coursework reference (CountVectorizer/TF-IDF/n-gram educational patterns):  
  https://github.com/nicolasenriquez/Data_Science_Portafolio/tree/main/data_science_specialization/Course%204%20-%20Text%20Mining

## Source-to-Decision Trace

1. Canonical procurement-cycle entity decomposition
- Decision: separate notice/line/bid/award/purchase-order/purchase-order-line contracts.
- Why: relational modeling and deterministic joins are clearer with explicit grain separation.
- Proposal artifacts:
  - `openspec/changes/expand-silver-procurement-cycle-and-feature-foundation-2026-04-22/design.md`
  - `openspec/changes/expand-silver-procurement-cycle-and-feature-foundation-2026-04-22/specs/silver-procurement-cycle/spec.md`

2. Optional notice-to-OC link contract
- Decision: model notice linkage as explicit optional relationship.
- Why: source evidence shows `CodigoLicitacion` sparsity; mandatory linkage would be incorrect.
- Evidence:
  - `docs/evidence/silver_procurement_cycle_grain_baseline_2026-04-22.md`

3. Silver boundary for deterministic feature foundations only
- Decision: allow deterministic derivations and versioned semantic annotations; disallow predictive business outputs.
- Why: preserves stage-gated architecture and avoids leakage/Gold overlap.
- Proposal artifacts:
  - `openspec/changes/expand-silver-procurement-cycle-and-feature-foundation-2026-04-22/specs/silver-feature-engineering-foundation/spec.md`

4. Task 5 NLP implementation boundary (feature extraction only)
- Decision: implement Silver NLP with deterministic text feature extraction workflows and annotation contracts, without supervised model training/prediction in Silver.
- Why: notebook references show vectorizer patterns and also supervised examples; Silver keeps only reproducible annotation features and TF-IDF artifact references.
- Proposal artifacts:
  - `openspec/changes/expand-silver-procurement-cycle-and-feature-foundation-2026-04-22/design.md`
  - `openspec/changes/expand-silver-procurement-cycle-and-feature-foundation-2026-04-22/specs/silver-feature-engineering-foundation/spec.md`

## Validation Linkage

- Evidence baseline:
  - `docs/evidence/silver_procurement_cycle_grain_baseline_2026-04-22.md`
- Architecture alignment:
  - `docs/architecture/data_architecture.md`
  - `docs/architecture/data_model.md`

## Problem

Omnibid has the facts needed to support supplier prioritization, but the current repository stops at deterministic Silver and read-only investigation contracts. That leaves a gap between "we know what happened" and "we can rank who should be contacted first, with evidence, at the right time".

The gap is not conceptual. It is operational:

- no time-aware candidate grain exists for supplier recommendation
- no explicit label hierarchy exists for participation, award, and materialization
- no leakage-safe feature registry exists for structured, text, and graph signals
- no baseline model selection protocol exists for out-of-time validation
- no Gold persistence contract exists for ranked candidates and run metadata

## Design Goals

1. Keep the Gold decision layer time-aware and leakage-safe.
2. Make the first release explainable and production-practical.
3. Use the existing Silver procurement-cycle facts as the only source of truth for labels.
4. Make structured, sparse text, and graph features first-class but separately inspectable.
5. Persist only Gold outputs and artifact references, not training state in Silver.
6. Keep the implementation additive and compatible with the current read-only workspace.

## Proposed Architecture

```text
Silver procurement-cycle facts
  -> candidate generation
  -> label builder
  -> feature registry
  -> deterministic preprocessing
  -> time-based model training and evaluation
  -> calibrated scoring
  -> Gold ranked outputs + evidence refs
```

```text
Gold ranked outputs
  -> existing investigation read model
  -> existing `/opportunities` / investigation read surfaces
  -> supplier-side decision support
```

### Candidate Row Contract

The first Gold model should rank suppliers for a procurement line at the grain:

`supplier_key × notice_id × item_code × snapshot_time`

The candidate set should be explicit, not an implicit cartesian product.

Positive candidates come from observed Silver evidence.

Negative candidates are sampled from an eligible supplier pool using a documented, reproducible rule set.

Candidate generation should prefer the union of:

- suppliers with historical participation in the same buyer, category, region, or procurement type
- suppliers retrieved as top-k textual neighbors for the line text
- suppliers connected through the procurement graph within one or two hops
- observed historical positives, which are always retained

The candidate set must be bounded and reproducible so training remains feasible at current data scale.

### Label Hierarchy

The Gold layer should treat labels as a hierarchy, not a single undifferentiated target.

| Label | Source of truth | Why it matters |
| --- | --- | --- |
| `participation_label` | `silver_bid_submission` and `silver_supplier_participation` | Highest coverage and the best first production target |
| `award_label` | `silver_award_outcome` | Closer to selection quality, but sparser |
| `materialization_label` | `silver_notice_purchase_order_link` and purchase-order line evidence | Closest to realized commercial value, but delayed |

The first production release should prioritize `participation_label` because it is the densest, earliest, and most actionable target.

`award_label` and `materialization_label` should be trained and evaluated in the same pipeline as benchmark and follow-on targets.

### Feature Families

#### Structured opportunity features

Examples:

- buyer key and contracting-unit key
- region and category
- procurement type and official status
- days to close / duration features
- estimated amount and amount bands
- complaint counts and administrative flags
- competition signals such as supplier count and bid count

#### Structured supplier history features

Examples:

- historical participation counts by buyer, category, region, and procurement type
- historical award counts and materialization counts
- recency and frequency features
- supplier activity concentration
- affinity to the current buyer or category

#### Interaction features

Examples:

- buyer-supplier affinity
- category-supplier affinity
- region overlap
- recency between historical matches and the current snapshot
- historical conversion rates for similar contexts

#### Sparse text features

Examples:

- line description text
- notice description text
- buyer item-spec text
- supplier item-spec text, when available

Use deterministic sparse representations such as word and char n-grams.
Keep these features sparse and versioned.
Do not persist dense embeddings in the first slice.

#### Graph features

Build a time-filtered heterogeneous procurement graph with nodes for:

- suppliers
- buyers
- contracting units
- categories
- notice lines

And edges for:

- participation
- award
- purchase-order materialization
- co-occurrence across buyer/category/region contexts

Use deterministic graph metrics such as:

- degree / weighted degree
- PageRank or related centrality
- common-neighbor counts
- path-based proximity features

Use NetworkX for the first implementation slice so graph construction and feature derivation stay deterministic and easy to inspect.

### Feature Selection and Normalization

Feature selection should be deterministic and documented, not ad hoc.

Recommended filters:

1. exclude any field whose availability is after the snapshot cutoff
2. exclude fields with extreme missingness or zero variance
3. collapse rare categories before encoding
4. remove highly collinear duplicates where a simpler field already captures the signal
5. keep an explicit allowlist for each feature family

Recommended normalization:

- use `log1p` or equivalent on heavy-tailed amounts and counts
- use explicit missingness flags for sparse numeric columns
- use one-hot encoding for low-cardinality categoricals
- use frequency encoding or another leakage-safe encoding for high-cardinality categoricals in the structured baseline
- use standardization or robust scaling for linear models
- keep sparse text features in sparse form

### Model Selection Order

The first release should follow a baseline-first order.

1. `LogisticRegression` or another calibrated linear classifier on structured + sparse features
2. `HistGradientBoostingClassifier` or equivalent tree-based nonlinear challenger on structured features
3. retrieval-only benchmark based on TF-IDF similarity for evidence recall
4. graph-augmented reranking on the same candidate set

The selected production model must win on out-of-time validation, not just on a random split.

Primary metrics:

- PR-AUC
- Recall@K
- MRR or NDCG@K
- calibration / Brier score
- slice-level lift by buyer, category, and region

### Gold Persistence Contract

The Gold layer should persist versioned outputs and metadata, not training state in Silver.

Recommended additive outputs:

| Table | Grain | Purpose |
| --- | --- | --- |
| `gold_procurement_line_investigation` | `notice_id + item_code` | line-level summary and investigation entrypoint |
| `gold_procurement_line_supplier_rank` | `supplier_key + notice_id + item_code + snapshot_time` | ranked candidate suppliers and scores |
| `gold_procurement_line_model_run` | model version + feature-set version + snapshot window | model metadata, metrics, and artifact refs |
| `gold_procurement_line_context` | `notice_id + item_code` | bounded evidence context for review and handoff |

Gold rows should store:

- score
- rank
- confidence band
- label family
- feature-set version
- model version
- snapshot cutoff
- evidence reference

Model artifacts, vectorizers, and graph snapshots should remain external artifacts with stable references.

### Serving Contract

The existing read-only investigation flow should consume Gold outputs without gaining write semantics.

The Gold layer should provide:

- ranked suppliers for a line
- explainable evidence references
- a summary row that can be consumed by the current workspace

It should not:

- mutate Silver
- auto-submit actions
- hide scores behind unversioned heuristics

## Alternatives Considered

1. Add a transformer-only semantic ranking stack first.
   - Rejected because it is heavier than needed for the first Gold slice and would bypass the existing deterministic contract.
2. Use only tabular features.
   - Rejected because text and graph evidence are already available and materially useful.
3. Train on a random split.
   - Rejected because it would leak future information and overstate performance.
4. Persist the training matrix and embeddings directly in Silver.
   - Rejected because Silver is metadata-only and reference-only.

## Risks

- Sparse labels may bias the model toward participation rather than realized commercial value.
- Time-based negative sampling can drift if the candidate-generation rules are not frozen.
- High-cardinality supplier and buyer features can dominate if they are not encoded carefully.
- Graph features can leak if the graph is not strictly time-filtered.
- A model that scores well globally may still underperform on critical buyer or category slices.

## Mitigations

- keep the label hierarchy explicit and versioned
- freeze candidate-generation rules with tests
- use leakage-safe preprocessing and allowlists
- evaluate by time slice and by business segment, not only globally
- retain retrieval-only and graph-only benchmarks so regressions are visible

## Migration Considerations

This change will likely require additive Gold tables or materialized views.

Any schema changes should be migration-backed and should not modify existing Silver tables.

If the first release can be served from views and artifact refs only, that is acceptable, but the Gold output contract must remain versioned and queryable.

## Validation Plan

- verify candidate generation and negative sampling with deterministic fixtures
- verify label derivation against Silver examples
- verify preprocessing rejects post-snapshot fields
- verify model selection uses out-of-time splits
- verify the chosen model is calibrated and reproducible
- verify Gold outputs round-trip through the read model or API contract
- verify Docker-first execution with the live database and test database

## 1. Contract and Documentation

- [ ] 1.1 Create the Gold decision-layer standard and its SDD note.
  Notes: the document must define the ranking grain, label hierarchy, feature families, model selection order, and Gold persistence contract.
  Acceptance: a future agent can read one standard and understand how Gold ranking works without reconstructing it from scattered docs.
- [ ] 1.2 Update the architecture and data-model docs to reflect the Gold line-ranking outputs.
  Notes: keep the existing read-only investigation contract and add the ranked-supplier layer as an additive Gold output.
  Acceptance: the repo clearly separates Silver facts from Gold ranked outputs.

## 2. Runtime and Dependencies

- [ ] 2.1 Add the ML runtime dependencies required by the Gold layer.
  Notes: add only the libraries needed for the first implementation slice, keeping the dependency set as small as practical.
  Acceptance: the project metadata can support feature assembly, ranking, and graph features without ad hoc local installs.
- [ ] 2.2 Add a versioned Gold config surface.
  Notes: capture candidate-generation limits, snapshot windows, thresholds, feature-set versions, and model metadata.
  Acceptance: the Gold pipeline does not rely on hard-coded constants for its core contract.

## 3. Gold Data and Features

- [ ] 3.1 Implement the time-aware candidate dataset builder.
  Notes: materialize rows at `supplier × notice_line × snapshot_time` and keep candidate generation reproducible.
  Acceptance: positive and negative examples are generated through explicit rules, not implicit cross joins.
- [ ] 3.2 Implement label derivation from Silver events.
  Notes: derive participation, award, and materialization labels from the current Silver procurement-cycle entities.
  Acceptance: the first production label is clearly identifiable and the auxiliary labels are benchmarked in the same pipeline.
- [ ] 3.3 Implement deterministic preprocessing and feature selection.
  Notes: include missingness handling, numeric transforms, categorical encoding, and leakage guards.
  Acceptance: post-snapshot fields are rejected and all feature families are versioned.
- [ ] 3.4 Implement sparse text retrieval features.
  Notes: use deterministic sparse representations for procurement line and specification text.
  Acceptance: the ranking pipeline can surface evidence from similar historical text without dense embeddings.
- [ ] 3.5 Implement graph feature generation.
  Notes: build a time-filtered heterogeneous procurement graph and derive deterministic graph metrics.
  Acceptance: graph features are reproducible and time-filtered.

## 4. Model Training and Evaluation

- [ ] 4.1 Implement the baseline model stack.
  Notes: start with a calibrated linear model and a tree-based challenger, then keep retrieval-only and graph-augmented benchmarks.
  Acceptance: the model shortlist is explicit and ordered.
- [ ] 4.2 Implement time-based validation and calibration.
  Notes: use out-of-time splits, calibration checks, and slice metrics by buyer, category, and region.
  Acceptance: the winner is chosen on time-aware metrics, not random-split metrics.
- [ ] 4.3 Persist model metadata and evaluation results.
  Notes: capture version, feature-set version, snapshot cutoff, metrics, and artifact references.
  Acceptance: every model run is reproducible and traceable.

## 5. Gold Outputs and Serving

- [ ] 5.1 Add additive Gold persistence for ranked suppliers and run metadata.
  Notes: keep the output contract versioned and additive, with no Silver mutation.
  Acceptance: the Gold result can be queried without exposing training state in Silver.
- [ ] 5.2 Wire the read-only investigation surface to consume Gold scores and evidence.
  Notes: preserve read-only semantics and keep the current workspace contract stable.
  Acceptance: the existing investigation flow can show ranked suppliers and evidence refs.

## 6. Validation and Handoff

- [ ] 6.1 Add unit and integration tests for leakage, ranking determinism, and persistence.
  Notes: cover label derivation, candidate generation, feature selection, and database-backed writes.
  Acceptance: the tests prove the new Gold guardrails without requiring manual inspection.
- [ ] 6.2 Run Docker-first validation on the live database and test database.
  Notes: keep the runtime contract explicit and fail fast on DB/env mismatch.
  Acceptance: the Gold slice is ready for implementation after the validation gates pass.

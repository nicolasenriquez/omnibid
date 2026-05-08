## 1. Contract and Sources

- [x] 1.1 Freeze the NLP standard in `docs/standards/nlp-standards.md`.
  Notes: use the official docs-backed stack choices and the repository's existing Silver boundary as the source of truth.
  Acceptance: the standard states the canonical libraries, the Silver persistence contract, and the downstream boundary.
- [x] 1.2 Record the decision in `docs/references/sdd-nlp-standards-2026-05-05.md`.
  Notes: capture the source URLs, the repository context, and the implementation boundary in one SDD note.
  Acceptance: the note is linkable from future implementation work.
- [x] 1.3 Update the official sources registry and engineering standards index.
  Notes: add the NLP-specific official docs and make the new standard discoverable from the main standards index.
  Acceptance: the repo points future agents to the NLP sources without re-discovery work.

## 2. Deterministic Pipeline Foundation

- [x] 2.1 Add `backend/nlp/` pipeline helpers.
  Notes: include normalization, language detection, token extraction, and artifact-building helpers.
  Acceptance: the pipeline is deterministic and versioned.
- [x] 2.2 Add `config/nlp/` versioned config and patterns.
  Notes: include model choice, thresholds, stopword policy, and rule-based entity patterns.
  Acceptance: config can be loaded without ad hoc constants in the pipeline code.
- [x] 2.3 Add the operator entrypoint `scripts/build_nlp_annotations.py`.
  Notes: keep the script backend-only and align it with the repo's container-first runtime.
  Acceptance: operators can run the annotation build without touching the frontend.
- [x] 2.4 Add explicit runtime-validation glue for the NLP job surface.
  Notes: keep source-profile and DB/env validation fail-fast before any persistence work starts.
  Acceptance: unsupported profiles or inconsistent runtime settings are rejected early.

## 3. Silver Contract Enforcement

- [x] 3.1 Wire the pipeline to the existing Silver annotation rows.
  Notes: write only the current metadata fields and artifact references.
  Acceptance: `nlp_version`, `corpus_scope`, tokens, n-grams, and `tfidf_artifact_ref` are handled deterministically.
- [x] 3.2 Enforce the no-vectors, no-scores Silver boundary.
  Notes: reject any attempt to persist dense vectors or prediction outputs in Silver.
  Acceptance: the boundary is covered by tests and fails fast on violations.
- [x] 3.3 Keep embeddings downstream only.
  Notes: sentence-transformers and Hugging Face outputs should land in artifacts or later Gold work, not Silver.
  Acceptance: the code path for embeddings is separated from Silver writes.

## 4. Runtime and Validation

- [ ] 4.1 Respect the repository `.env` and `.env.docker` database contract.
  Notes: use `DATABASE_URL` and `TEST_DATABASE_URL` as defined by the repo, with Docker service DNS for containerized runs.
  Acceptance: tests and scripts behave the same way in local and Docker contexts.
- [ ] 4.2 Add unit tests for normalization, language detection, and vectorizer behavior.
  Notes: keep the tests deterministic and independent of the full pipeline runner.
  Acceptance: the tests fail before the pipeline exists and pass once the contract is implemented.
- [ ] 4.3 Add database-backed tests if the implementation writes Silver rows.
  Notes: test the exact write contract instead of relying on mocks only.
  Acceptance: the persistence behavior is verified against the test database.
- [ ] 4.4 Run Docker-first quality gates.
  Notes: use the smallest relevant gate first, then broaden only if needed.
  Acceptance: validation evidence is captured before implementation is considered done.

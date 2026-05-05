## Problem

The repository already has the Silver contract for procurement text annotations, but the implementation boundary is still split across docs, pipeline wrappers, runtime config, and investigation notes. That makes it too easy to drift toward ad hoc tokenization, inconsistent language detection, or accidental persistence of dense vectors and model outputs in Silver.

The implementation also needs to respect the repository's database runtime contract:

- local `.env` uses localhost
- Docker `.env.docker` uses `db` and `db_test`
- tests require a separate test database URL
- Docker is the canonical runtime for backend and database-backed work

## Design Goals

1. Keep Silver annotation rows deterministic and versioned.
2. Use official docs-backed library choices only.
3. Keep dense embeddings and reranker outputs out of Silver.
4. Keep the implementation schema-neutral in the first slice.
5. Make the runtime fail fast on missing config, model paths, or DB targets.
6. Add code-level guardrails around the NLP surface without a broad refactor.

## Proposed Architecture

```text
raw procurement text
  -> explicit UTF-8 decode
  -> Unicode NFKC normalization
  -> whitespace collapse
  -> fastText language identification
  -> spaCy Spanish pipeline
  -> CountVectorizer / TfidfVectorizer
  -> Silver annotation rows + external TF-IDF artifact
```

```text
procurement text that needs semantic embeddings
  -> Sentence Transformers or Hugging Face pipeline
  -> external artifact or downstream Gold layer
```

### Component Boundaries

- `backend/nlp/`
  - deterministic pipeline assembly, normalization helpers, language detection, and artifact builders.
- `config/nlp/`
  - versioned config, stopword/pattern files, and model selection.
- `backend/pipeline/`
  - orchestration helpers and runtime glue for the NLP entrypoint.
- `backend/core/config.py`
  - environment loading and DB/runtime validation helpers.
- `scripts/build_nlp_annotations.py`
  - operator entrypoint for refresh/build execution.
- `tests/unit/`
  - deterministic contract tests for normalization, hashing, and vectorization.
- `tests/integration/`
  - database-backed persistence verification when needed.

### Model and Library Choices

#### spaCy

Use spaCy for tokenization, lemmatization, POS tagging, and entity recognition because the official docs provide the exact pipeline semantics needed for deterministic annotations.

The Spanish model choice should default to `es_core_news_md` because it is the repository's best fit for core vocabulary, syntax, entities, and vectors.

The pipeline should use registered components, not custom one-off processing code. If rule-based procurement entities are needed, use `EntityRuler` with versioned patterns.

#### fastText

Use `lid.176.ftz` for offline language identification after UTF-8 normalization.
Reject or downgrade low-confidence results to `und` rather than pretending the language is known.

#### scikit-learn

Use `CountVectorizer` and `TfidfVectorizer` for deterministic lexical features.
Persist only the artifact reference in Silver, not the vectors themselves.

#### NLTK

Allow Snowball stemming as an auxiliary baseline only.
Do not make stemming the canonical business representation.

#### Sentence Transformers and Hugging Face

Use these only for downstream embeddings, semantic search, token classification, or reranking.
Do not persist their dense outputs in Silver.

## Alternatives Considered

1. Transformer-only NLP stack.
   - Rejected because it is heavier than needed for the Silver contract and does not align with the repository's metadata-only persistence rule.
2. NLTK-only pipeline.
   - Rejected because it would require more manual assembly and is less aligned with the repository's canonical Spanish pipeline needs.
3. Persist embeddings in Silver.
   - Rejected because it violates the current Silver boundary and would blur deterministic annotation with semantic feature storage.
4. Introduce new Silver tables immediately.
   - Rejected for the first slice because the current schema already covers the intended annotation contract.

## Risks

- If the canonical spaCy model changes, downstream annotations may drift.
- If the language-ID threshold is too strict, valid Spanish procurement text may fall back to `und`.
- If the pipeline tries to store dense vectors, Silver will become too large and too ambiguous.
- If Docker and host `.env` values diverge, tests may pass in one environment and fail in the other.

## Mitigations

- keep `nlp_version` explicit and bump it when behavior changes
- keep the language-ID threshold configurable and covered by tests
- validate the Silver write contract before persistence
- keep `.env.example` and `.env.docker` aligned with the runtime contract
- use Docker-first validation for DB-backed work

## Migration Considerations

The first slice should not require a schema migration.
If future work needs `language_confidence`, POS payloads, entity payloads, or embedding references persisted explicitly, that should be a separate additive proposal with explicit migration review.

## Validation Plan

- verify normalization and hash stability with unit tests
- verify fastText UTF-8 language detection behavior with unit tests
- verify vectorizer configuration and artifact naming with unit tests
- verify entrypoint routing and DB/env validation before persistence
- verify DB writes against the test database when persistence is exercised
- run Docker-first smoke checks before wider quality gates

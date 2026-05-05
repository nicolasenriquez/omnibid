## Why

Omnibid already has a Silver text-annotation contract for procurement text, but the actual NLP stack and boundary are still spread across docs, pipeline wrappers, runtime config, and implementation assumptions. The repo now needs one source-backed change that both documents the contract and hardens the code path that enforces it, so Spanish procurement text is processed the same way everywhere.

The intended implementation is narrow:

- keep Silver metadata-only and reference-only
- use spaCy as the canonical Spanish linguistic pipeline
- use fastText for offline language detection on UTF-8 text
- use scikit-learn for deterministic counts and TF-IDF artifacts
- add code-level pipeline/runtime validation around the existing NLP surface
- keep Sentence Transformers, Hugging Face tokenizers, and Transformers outside Silver
- respect the existing `.env` / `.env.docker` database contract instead of introducing a second runtime configuration path

## What Changes

- Add `docs/standards/nlp-standards.md` and the corresponding SDD note in `docs/references/`.
- Add a backend NLP package for deterministic procurement text processing.
- Add a config surface for NLP versioning, model selection, and feature extraction defaults.
- Add an operator script to build or refresh the existing Silver annotation rows.
- Add explicit runtime-validation helpers for the NLP job entrypoint and the DB/env split.
- Add tests for normalization, language detection, deterministic vectorization, Silver boundary enforcement, and runtime validation.
- Keep the current Silver schema unchanged in the first slice.
- Keep dense embeddings and reranker outputs outside Silver.
- Keep the implementation Docker-first and fail-fast.

## Capabilities

### New Capabilities

- `nlp-standard-documentation`
- `deterministic-spanish-nlp-pipeline`
- `silver-text-annotation-contract`
- `downstream-semantic-artifact-boundary`
- `nlp-runtime-validation`

### Modified Capabilities

- None.

## Context

The repository already defines the Silver text annotation entities and the metadata-only contract:

- `silver_notice_text_ann`
- `silver_notice_line_text_ann`
- `silver_purchase_order_line_text_ann`

The current model and architecture docs already require:

- explicit `nlp_version`
- token and n-gram payloads only
- `tfidf_artifact_ref` reference strings only
- no serialized vectors in Silver
- no predictive business scores in Silver

The runtime configuration also already exists:

- `backend/core/config.py` loads `.env`
- `.env.example` is the local host template
- `.env.docker` is the Docker runtime template
- Docker database hosts must be `db` and `db_test`, not `localhost`

This change should codify that contract in code, tests, and docs rather than redesign it.

## Verified Official Sources

1. `https://spacy.io/api/language/`
   - Pipeline orchestration and custom component registration.
2. `https://spacy.io/usage/linguistic-features`
   - Tokenization, POS, lemmatization, and entity annotations.
3. `https://spacy.io/models/es/`
   - Spanish model families and the canonical `es_core_news_md` candidate.
4. `https://spacy.io/api/entityruler`
   - Rule-based named entity augmentation.
5. `https://fasttext.cc/docs/en/language-identification`
   - UTF-8 language identification and the `lid.176` model family.
6. `https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.CountVectorizer.html`
   - Deterministic token counts and n-gram extraction.
7. `https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html`
   - TF-IDF feature generation.
8. `https://www.nltk.org/api/nltk.stem.SnowballStemmer.html`
   - Spanish stemming as an auxiliary baseline only.
9. `https://huggingface.co/docs/tokenizers/pipeline`
   - Normalization and subword tokenization pipeline stages.
10. `https://huggingface.co/docs/transformers/main_classes/pipelines`
    - Token classification and feature extraction pipelines.
11. `https://sbert.net/docs/sentence_transformer/usage/usage.html`
    - Fixed-size embeddings and semantic search use cases.
12. `https://docs.pydantic.dev/latest/concepts/pydantic_settings/`
    - `.env` loading and environment-variable precedence.

## Non-Goals

- No supervised model training in Silver.
- No dense vector persistence in Silver.
- No frontend work.
- No new public API routes.
- No schema rewrite for the existing Silver annotation tables in this slice.
- No replacement of the current raw / normalized pipeline.
- No Gold ranking or decision-model serving in this slice; that work lives in `gold-procurement-line-ranking`.

## Impact

- `docs/standards/nlp-standards.md`
- `docs/references/sdd-nlp-standards-2026-05-05.md`
- `docs/references/sdd-official-sources-registry.md`
- `docs/standards/engineering_standards.md`
- `backend/nlp/`
- `config/nlp/`
- `backend/pipeline/`
- `backend/core/config.py`
- `scripts/build_nlp_annotations.py`
- `tests/unit/test_nlp_*.py`
- `tests/integration/test_nlp_*.py`
- `justfile`

Not impacted in this slice:

- `client/`
- `backend/api/routers/`
- `backend/models/normalized.py` schema definitions
- `alembic/versions/`
- existing Silver table names and grain contracts

## Goals

- Make the NLP stack official, source-backed, and reproducible.
- Keep Silver annotations deterministic and metadata-only.
- Make the runtime contract explicit for Docker and host execution.
- Add code-level guardrails around the NLP pipeline surface instead of relying only on docs.
- Preserve the current Silver boundary while enabling later Gold or artifact-only work.

## Open Questions

- Should `es_core_news_md` be pinned as the only canonical spaCy Spanish model, or should a lighter smoke-test fallback be allowed?
- Should the runtime validation live in `backend/core/config.py`, `backend/pipeline/`, or the new NLP package itself?
- Should downstream embeddings be stored only as artifact references, or should a later Gold change define persistent embedding tables?
- Should any future `language_confidence` field be persisted, or remain runtime-only telemetry?

## Validation Strategy

- unit tests for normalization and hash determinism
- unit tests for fastText language detection thresholds and `und` fallback
- unit tests for CountVectorizer / TfidfVectorizer configuration
- unit tests for source-profile or job-entrypoint routing and DB/env validation
- database-backed tests for Silver persistence if the slice writes rows
- Docker-first smoke checks before any broader quality gate

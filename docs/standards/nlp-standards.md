# NLP Standard: deterministic procurement text features and Silver boundary

## Overview

Omnibid uses a deterministic, Silver-first NLP stack for procurement text.
The purpose of this standard is to keep text processing reproducible, versioned, and auditable while preventing semantic or predictive outputs from leaking into Silver.

The canonical stack is:

- spaCy for Spanish tokenization, POS tagging, lemmatization, and named entity recognition
- fastText for offline language identification on UTF-8 text
- scikit-learn for deterministic count and TF-IDF feature extraction
- NLTK only as an auxiliary stemming library
- Sentence Transformers, Hugging Face Tokenizers, and Hugging Face Transformers only for downstream semantic work outside Silver

For spaCy-specific pipeline and rule-based contracts, see [spaCy standard](spacy-standard.md).
For supervised fastText classification and model-size contracts, see [fastText standard](fasttext-standard.md).

## Scope

This standard applies to:

- procurement text normalization and language detection
- token, lemma, POS, NER, and n-gram extraction
- Silver annotation writes for notices, notice lines, and purchase-order lines
- downstream embeddings or reranking artifacts that may be produced later
- the configuration and runtime surfaces that execute these NLP jobs

This standard does not define business scoring, ranking, or forecasting.
Those outputs belong in downstream Gold or feature-serving layers.

## Source Priority

Use sources in this order:

1. Official documentation for the relevant library or framework
2. Repository contracts in `docs/architecture/`, `docs/runbooks/`, and `backend/models/`
3. Repository environment files and settings code
4. Secondary articles only when the official docs do not cover the behavior

## Repository Context

The repository already has the Silver annotation tables and the contract boundary.
The implemented data model currently stores:

- `silver_notice_text_ann`
- `silver_notice_line_text_ann`
- `silver_purchase_order_line_text_ann`

The current contract is metadata-only:

- explicit `nlp_version`
- deterministic token and n-gram payloads
- `tfidf_artifact_ref` reference strings only
- no serialized vectors in Silver
- no business prediction scores in Silver

The runtime configuration is also already standardized:

- `backend/core/config.py` loads settings from `.env`
- local `.env.example` uses localhost database settings
- `.env.docker` uses Docker service DNS names `db` and `db_test`
- `TEST_DATABASE_URL` must remain separate from `DATABASE_URL`

Any NLP job that persists to the database must respect that runtime split.
Docker is the canonical execution path for full-stack and database-backed work.

## Canonical Stack

### spaCy

Use spaCy as the canonical NLP library for Spanish text processing.
The current official Spanish model family includes `es_core_news_sm`, `es_core_news_md`, `es_core_news_lg`, and `es_dep_news_trf`.

The canonical default for this repository is `es_core_news_md` because it provides core vocabulary, syntax, entities, and vectors.

Use spaCy for:

- tokenization
- part-of-speech tagging
- lemmatization
- named entity recognition
- rule-based entity augmentation through `EntityRuler`

Lemmatization must respect spaCy v3 behavior:

- lemmas are not guaranteed by default
- rule-based lemmatization requires prior POS assignment

That means the pipeline order matters. If the lemmatizer depends on POS, POS must run first.

### fastText

Use fastText for offline language identification.
The official language-identification models recognize 176 languages and are trained on UTF-8 data, so input must be normalized to UTF-8 before detection.

The canonical model for this repository is `lid.176.ftz` because it is compressed and practical for containerized batch jobs.

Use fastText for:

- language detection
- low-cost confidence gating
- fallback to `und` when the text is too short or confidence is below threshold

### scikit-learn

Use scikit-learn for deterministic lexical feature extraction.
`CountVectorizer` and `TfidfVectorizer` both support n-gram extraction and sparse document-term matrices.

Use scikit-learn for:

- count-based token and n-gram extraction
- TF-IDF artifact generation
- versioned, reproducible feature fit/transform workflows

Only the artifact reference is persisted in Silver.
The actual sparse or dense vector outputs belong in external artifacts or downstream layers.

### NLTK

Use NLTK only as an auxiliary tool.
The repository may use Snowball stemming for Spanish as a baseline or comparison path, but stemming is not the canonical Silver representation.

Do not make NLTK the primary NLP stack for Spanish procurement text.

### Sentence Transformers and Hugging Face

Sentence Transformers is allowed for downstream embeddings, semantic search, clustering, or reranking.
Hugging Face Tokenizers and Transformers are allowed for downstream subword tokenization, token classification, and reranking workflows.

These tools are not the canonical Silver representation.
They must not persist dense vectors, reranker scores, or model outputs as Silver business truth.

## Text Normalization Contract

Input text should follow this order:

1. decode the source text explicitly
2. normalize to UTF-8
3. apply Unicode NFKC normalization
4. collapse repeated whitespace
5. trim edges
6. use a lowercase working copy for feature extraction
7. preserve the original business text and accents in source-aligned fields

Do not strip accents from the canonical business text.
If a search-oriented derived copy needs accent stripping, keep it as a separate derived field and do not overwrite the source text.

## Silver Persistence Contract

Silver annotation rows may store:

- `source_file_id`
- `row_hash_sha256`
- `nlp_version`
- `corpus_scope`
- `language_detected`
- token and lemma payloads
- n-gram payloads
- semantic category labels
- artifact references

Silver annotation rows must not store:

- serialized dense vectors
- prediction probabilities
- business ranking scores
- training state
- opaque model blobs

If a future implementation needs POS or entity payloads beyond the current table contract, that data should go to an explicit artifact or a separately approved additive schema change.

## DB and Runtime Contract

The database and runtime surface must remain fail-fast and environment-driven.

- local development uses the host `.env` pattern
- Docker development uses `.env.docker`
- containerized database hosts use `db` and `db_test`
- tests use `TEST_DATABASE_URL`
- production-like scripts must never hardcode `localhost` when running inside Docker

If the NLP job cannot load its required settings, model, or database target, it must fail immediately instead of falling back silently.

## Validation Rules

Minimum validation for any NLP change:

- unit tests for deterministic normalization and hashing
- unit tests for language detection thresholds and fallback behavior
- unit tests for vectorizer configuration
- database-backed tests when a job writes Silver rows
- container-first execution for runtime verification

Recommended gate order:

1. `rtk just docker-start`
2. `rtk just docker-smoke`
3. targeted backend tests
4. `rtk just ci-fast`
5. `rtk just ci`

## Implementation Targets

The implementation surface for this standard should live under:

- `backend/nlp/`
- `config/nlp/`
- `scripts/build_nlp_annotations.py`
- `tests/unit/test_nlp_*.py`
- `docs/references/sdd-nlp-standards-2026-05-05.md`

The current Silver tables do not need a schema change to adopt this boundary.
If a future feature needs new persisted NLP columns, that should be a separate migration-backed proposal.

## Official Sources Consulted

| Source | Topic | Decision |
| --- | --- | --- |
| https://spacy.io/api/language/ | Pipeline orchestration and custom components | Use spaCy `Language` pipelines and registered components rather than ad hoc text processing |
| https://spacy.io/usage/linguistic-features | POS, lemmatization, token annotations | Require POS before rule-based lemmatization and keep linguistic annotations explicit |
| https://spacy.io/models/es/ | Spanish model families | Default to `es_core_news_md` for canonical Spanish processing |
| https://spacy.io/api/entityruler | Rule-based entities | Allow rule-based procurement entity augmentation with versioned patterns |
| https://spacy.io/usage/rule-based-matching/ | Pattern matching rules | Use pattern-based augmentation where deterministic matching is safer than training |
| https://fasttext.cc/docs/en/language-identification | Language ID and UTF-8 input | Detect language with fastText after UTF-8 normalization |
| https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.CountVectorizer.html | Count-based features and n-grams | Use `CountVectorizer` for deterministic token and n-gram extraction |
| https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html | TF-IDF features | Use `TfidfVectorizer` to build reference-only TF-IDF artifacts |
| https://www.nltk.org/api/nltk.stem.SnowballStemmer.html | Spanish stemming support | Keep Snowball stemming auxiliary only |
| https://huggingface.co/docs/tokenizers/pipeline | Normalization, pre-tokenization, model, post-processing | Treat subword tokenization as a separate downstream branch |
| https://huggingface.co/docs/transformers/main_classes/pipelines | Token classification and feature extraction pipelines | Keep Transformer-based NLP outside Silver persistence |
| https://sbert.net/docs/sentence_transformer/usage/usage.html | Fixed-size embeddings and semantic search | Allow embeddings only in downstream artifact or Gold layers |
| https://docs.pydantic.dev/latest/concepts/pydantic_settings/ | `.env` loading and settings precedence | Keep settings environment-driven and fail-fast |

## Notes

The current repo already has the Silver annotation contract, so this standard is not introducing new business semantics.
It is making the source-backed implementation boundary explicit before the next OpenSpec change lands.

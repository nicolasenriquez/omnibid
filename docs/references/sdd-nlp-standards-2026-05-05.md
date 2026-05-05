# SDD Reference Note

## Metadata

- Change/Proposal: nlp-standard-and-pipeline-foundation
- Date: 2026-05-05
- Author: Codex
- Area (backend/db/pipeline/api/tooling): backend / pipeline / docs / runtime

## Question

- Which NLP libraries and persistence boundaries should Omnibid standardize for procurement text annotations, and how should the database `.env` runtime contract be respected?

## Official Sources Consulted

1. https://spacy.io/api/language/
   - Section/topic: pipeline orchestration and custom components
   - Relevant contract: spaCy pipelines are ordered text-processing objects and custom components should be registered on the `Language` pipeline
2. https://spacy.io/usage/linguistic-features
   - Section/topic: tokenization, POS, lemmatization, and entity annotations
   - Relevant contract: lemmatization in spaCy v3 depends on prior POS assignment when using rule-based lemmatization
3. https://spacy.io/models/es/
   - Section/topic: Spanish trained pipelines
   - Relevant contract: `es_core_news_md` is the canonical Spanish model family candidate for core vocabulary, syntax, entities, and vectors
4. https://fasttext.cc/docs/en/language-identification
   - Section/topic: language identification
   - Relevant contract: the `lid.176` models expect UTF-8 input and the compressed `ftz` model is suitable for lightweight batch use
5. https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.CountVectorizer.html
   - Section/topic: token counts and n-grams
   - Relevant contract: deterministic sparse token and n-gram extraction should use scikit-learn vectorizers
6. https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html
   - Section/topic: TF-IDF feature extraction
   - Relevant contract: TF-IDF artifacts can be generated from the same deterministic text corpus and persisted as references only
7. https://www.nltk.org/api/nltk.stem.SnowballStemmer.html
   - Section/topic: Spanish stemming
   - Relevant contract: NLTK SnowballStemmer supports Spanish but should remain auxiliary
8. https://huggingface.co/docs/tokenizers/pipeline
   - Section/topic: tokenization pipeline stages
   - Relevant contract: normalization, pre-tokenization, model, and post-processing should be treated as a separate downstream tokenization branch
9. https://huggingface.co/docs/transformers/main_classes/pipelines
   - Section/topic: transformer inference pipelines
   - Relevant contract: token classification and feature extraction pipelines are allowed for downstream work, not Silver persistence
10. https://sbert.net/docs/sentence_transformer/usage/usage.html
    - Section/topic: embeddings and semantic search
    - Relevant contract: sentence-transformers produce fixed-size embeddings that should live outside Silver
11. https://docs.pydantic.dev/latest/concepts/pydantic_settings/
    - Section/topic: `.env` loading and settings precedence
    - Relevant contract: environment-driven settings should load from `.env`/secrets files and keep environment variables authoritative

## Repository Context Consulted

1. `backend/core/config.py`
   - Section/topic: repository settings loader
   - Relevant contract: Omnibid already loads settings from `.env` and uses `DATABASE_URL` plus `TEST_DATABASE_URL`
2. `.env.example`
   - Section/topic: local runtime template
   - Relevant contract: local development uses localhost database URLs
3. `.env.docker`
   - Section/topic: Docker runtime template
   - Relevant contract: Docker runtime uses service DNS names `db` and `db_test`
4. `docs/architecture/data_model.md`
   - Section/topic: Silver annotation contract
   - Relevant contract: the repository already defines versioned text annotation tables and TF-IDF reference-only persistence
5. `docs/architecture/data_architecture.md`
   - Section/topic: Silver boundary rules
   - Relevant contract: Silver excludes predictive outputs and serialized vectors

## Decision

- What was implemented: created `docs/standards/nlp-standards.md`, updated the official sources registry, and recorded the standardization decision in a repo-local SDD note so the next OpenSpec change can build from explicit contracts.
- Why this matches official source: the official docs support spaCy as the canonical linguistic pipeline, fastText as a UTF-8 language-ID tool, scikit-learn for deterministic counts and TF-IDF, NLTK only as a stemmer, and Sentence Transformers / Hugging Face only as downstream embedding or token-classification tools. The repo docs already require Silver to store only metadata and artifact references.

## Code Impact

- Files touched:
  - `docs/standards/nlp-standards.md`
  - `docs/references/sdd-nlp-standards-2026-05-05.md`
  - `docs/references/sdd-official-sources-registry.md`
  - `docs/standards/engineering_standards.md`
- Behavioral impact:
  - no runtime behavior changed yet
  - the standard makes the Silver NLP boundary explicit before implementation work begins

## Validation

- Tests/checks executed:
  - reviewed existing Silver annotation contract and `.env` runtime files
  - checked official documentation for each referenced library
- Result:
  - documentation-only change prepared successfully

## Notes / Risks

- Open questions:
  - whether downstream embeddings should become artifact-only or a separate Gold table family
  - whether a future migration should persist `language_confidence` or additional POS/NER payloads
- Follow-up actions:
  - generate the OpenSpec proposal for the NLP pipeline boundary and implementation package
  - keep the first code slice schema-neutral unless a future migration is explicitly approved

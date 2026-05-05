# SDD Reference Note

## Metadata

- Change/Proposal: customer-analytics-standards-foundation
- Date: 2026-05-05
- Author: Codex
- Area (backend/db/pipeline/api/tooling): docs / backend / db / pipeline / runtime

## Question

- Which official docs and repository contracts should define the customer analytics standard for Omnibid, and what runtime/database facts need to be documented before implementation starts?

## Official Sources Consulted

1. https://docs.python.org/3/library/csv.html
   - Topic/section: CSV file reading and writing
   - Relevant contract: explicit CSV dialects, `DictReader`, newline handling, and quoted-delimiter parsing
2. https://docs.python.org/3/library/hashlib.html
   - Topic/section: secure hashes and message digests
   - Relevant contract: SHA-256 for file and row identity hashes
3. https://docs.python.org/3/library/pathlib.html
   - Topic/section: object-oriented filesystem paths
   - Relevant contract: explicit `Path` handling for dataset-root discovery and file traversal
4. https://docs.python.org/3/library/argparse.html
   - Topic/section: command-line parsing
   - Relevant contract: explicit operator entrypoints with fail-fast argument handling
5. https://docs.python.org/3/library/json.html
   - Topic/section: JSON encoding and decoding
   - Relevant contract: stable JSON artifacts for profiling and state files
6. https://docs.python.org/3/library/datetime.html
   - Topic/section: date and time types
   - Relevant contract: explicit timestamp and UTC handling
7. https://docs.python.org/3/library/unicodedata.html
   - Topic/section: Unicode normalization
   - Relevant contract: explicit text normalization behavior for procurement text cleaning
8. https://docs.pydantic.dev/latest/concepts/pydantic_settings/
   - Topic/section: settings loading and `.env` precedence
   - Relevant contract: environment-driven config with explicit file precedence
9. https://docs.sqlalchemy.org/en/20/dialects/postgresql.html
   - Topic/section: PostgreSQL insert and ON CONFLICT support
   - Relevant contract: deterministic upserts using explicit conflict targets
10. https://docs.sqlalchemy.org/en/20/orm/session_api.html
    - Topic/section: session and transaction API
    - Relevant contract: transaction-aware batch writes and commit/rollback behavior
11. https://alembic.sqlalchemy.org/en/latest/
    - Topic/section: migration environment and revision flow
    - Relevant contract: Alembic as schema source of truth
12. https://www.postgresql.org/docs/16/sql-insert.html
    - Topic/section: INSERT and ON CONFLICT
    - Relevant contract: database-level upsert semantics and atomic conflict handling
13. https://www.postgresql.org/docs/16/datatype-numeric.html
    - Topic/section: numeric types
    - Relevant contract: precise storage for amounts and quantities
14. https://spacy.io/api/language/
    - Topic/section: pipeline orchestration
    - Relevant contract: registered spaCy pipelines and components for deterministic NLP
15. https://spacy.io/api/entityruler
    - Topic/section: rule-based entity augmentation
    - Relevant contract: deterministic procurement entity augmentation when needed
16. https://spacy.io/models/es/
    - Topic/section: Spanish model families
    - Relevant contract: Spanish pipeline choice must be grounded in the official model family guidance
17. https://fasttext.cc/docs/en/language-identification
    - Topic/section: language identification
    - Relevant contract: UTF-8 input expectation and compressed `lid.176.ftz` model guidance
18. https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.CountVectorizer.html
    - Topic/section: count-based text features
    - Relevant contract: deterministic count and n-gram extraction
19. https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html
    - Topic/section: TF-IDF features
    - Relevant contract: reference-only TF-IDF artifact generation
20. https://www.nltk.org/api/nltk.stem.SnowballStemmer.html
    - Topic/section: Spanish stemming
    - Relevant contract: stemming is auxiliary only
21. https://sbert.net/docs/sentence_transformer/usage/usage.html
    - Topic/section: embeddings and semantic search
    - Relevant contract: embeddings belong downstream of Silver
22. https://huggingface.co/docs/tokenizers/pipeline
    - Topic/section: tokenization pipeline stages
    - Relevant contract: tokenization is a separate downstream branch
23. https://huggingface.co/docs/transformers/main_classes/pipelines
    - Topic/section: inference pipelines
    - Relevant contract: transformer outputs stay outside Silver
24. https://www.chilecompra.cl/datos-abiertos/
    - Topic/section: Datos Abiertos overview
    - Relevant contract: historical/open-data source profile for procurement analytics
25. https://www.chilecompra.cl/api/
    - Topic/section: API overview
    - Relevant contract: operational query-oriented source profile
26. https://www.mercadopublico.cl/Home/Contenidos/QueEsLicitacion
    - Topic/section: licitation definition
    - Relevant contract: official terminology for tender semantics
27. https://www.mercadopublico.cl/Home/
    - Topic/section: public portal home
    - Relevant contract: portal is a human-facing surface with frequently refreshed information

## Repository Context Consulted

1. `docs/architecture/data_architecture.md`
   - Topic/section: layer intent and Silver boundary
   - Relevant contract: Raw/Normalized/Silver separation and metadata-only annotations
2. `docs/architecture/data_model.md`
   - Topic/section: implemented baseline and semantic annotation entities
   - Relevant contract: `silver_*_text_ann` tables and `tfidf_artifact_ref` behavior
3. `docs/business/data_sources_downloads_vs_api.md`
   - Topic/section: source profile split
   - Relevant contract: CSV downloads are historical; API is operational and query-oriented
4. `docs/business/downloaded_csv_contracts.md`
   - Topic/section: observed CSV headers and grain hypotheses
   - Relevant contract: current CSV drop assumptions and validation tasks
5. `docs/business/api_contracts_market_public.md`
   - Topic/section: API access patterns and key fields
   - Relevant contract: operational API contract distinct from monthly CSV downloads
6. `backend/core/config.py`
   - Topic/section: settings loader
   - Relevant contract: `.env`-driven `DATABASE_URL` and `TEST_DATABASE_URL`
7. `.env`
   - Topic/section: host runtime values
   - Relevant contract: local `localhost` database URLs and host dataset path
8. `.env.docker`
   - Topic/section: Docker runtime values
   - Relevant contract: service DNS database URLs and container dataset path
9. `docker-compose.yml`
   - Topic/section: runtime services
   - Relevant contract: effective database runtime is `postgres:16-alpine`, with `db` and `db_test` service DNS names
10. `scripts/profile_raw.py`
    - Topic/section: CSV profiling entrypoint
    - Relevant contract: `latin1` + `;` CSV profiling, required column validation, file profiles
11. `scripts/ingest_raw.py`
    - Topic/section: raw ingestion entrypoint
    - Relevant contract: file/row hashes, lineage fields, raw ingestion batching, and compatibility with `orden_compra` / `orden-compra`
12. `scripts/build_normalized.py`
    - Topic/section: normalized/silver build entrypoint
    - Relevant contract: deterministic upserts, conflict keys, and quality gate wiring
13. `backend/normalized/transform.py`
    - Topic/section: identity resolution and text annotation builders
    - Relevant contract: buyer/supplier/category identity keys and `tfidf://` annotation references
14. `backend/models/normalized.py`
    - Topic/section: normalized and Silver table definitions
    - Relevant contract: metadata-only text annotations and explicit business keys
15. `backend/normalized/upsert_engine.py`
    - Topic/section: upsert guardrails
    - Relevant contract: conflict-key enforcement and Silver leakage guards
16. `backend/normalized/quality_gate.py`
    - Topic/section: quality gate evaluation
    - Relevant contract: fail/pass/warn decisions and error-rate thresholding
17. `backend/shared/cleaning.py`
    - Topic/section: text normalization helpers
    - Relevant contract: current Unicode decomposition and whitespace normalization behavior

## Decision

- What was implemented: created a new `docs/standards/customer-analytics-standards.md`, recorded the source-backed decision in a new SDD note, updated the official sources registry with the missing Python standard-library links used by the pipeline, and aligned the PostgreSQL baseline doc with the effective Compose runtime.
- Why this matches official source: the official docs show the exact contracts needed for the current repo shape - CSV parsing, SHA-256 hashing, `Path` handling, environment-driven settings, SQLAlchemy/PostgreSQL upserts, Alembic migrations, deterministic Spanish NLP, and the ChileCompra/Mercado Publico source split.

## Code Impact

- Files touched:
  - `docs/standards/customer-analytics-standards.md`
  - `docs/references/sdd-customer-analytics-standards-2026-05-05.md`
  - `docs/references/sdd-official-sources-registry.md`
  - `docs/standards/postgres-standard.md`
- Behavioral impact:
  - no runtime behavior changed
  - the repo now has a source-backed procurement analytics standard that matches the current Docker and `.env` contract
  - PostgreSQL docs now match the effective Compose baseline instead of the stale 18-alpine wording

## Validation

- Tests/checks executed:
  - reviewed the current `.env`, `.env.docker`, `docker-compose.yml`, `backend/core/config.py`, and the CSV / normalized / NLP pipeline code
  - verified the current official documentation for the referenced Python modules, database stack, NLP stack, and ChileCompra/Mercado Publico sources
- Result:
  - documentation-only change prepared successfully

## Notes / Risks

- Open questions:
  - whether `api_json` and `open_data_snapshot` should become concrete ingestion adapters in a future change or remain source-profile contracts only
  - whether any future schema work should persist additional NLP metadata such as confidence or POS payloads
- Follow-up actions:
  - start the OpenSpec proposal for the implementation slice that follows this standard
  - keep the next code slice schema-neutral unless a new migration is explicitly approved

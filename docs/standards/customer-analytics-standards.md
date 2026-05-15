# Customer Analytics Standards: procurement source contracts, deterministic pipeline, and Silver boundary

## Purpose

This standard defines how Omnibid handles procurement analytics from the source contract through Raw, Normalized, and Silver so future agents do not mix CSV snapshots, API queries, and downstream semantic work.

The goal is not to redesign the platform. The goal is to make the current contracts explicit, source-backed, and easy to validate.

## Scope

This standard applies to:

- `scripts/profile_raw.py`
- `scripts/ingest_raw.py`
- `scripts/build_normalized.py`
- `backend/core/config.py`
- `backend/pipeline/extract/`
- `backend/pipeline/transform/`
- `backend/pipeline/load/`
- `backend/pipeline/shared/`
- `backend/models/`
- `docs/architecture/`
- `docs/business/`
- `docs/references/`
- `docs/evidence/`

This standard does not define:

- Gold scoring or forecasting
- frontend behavior
- notebook-only experimentation
- ad hoc source mixing without an explicit adapter contract

## Existing Repo Contracts

This standard composes the existing repository docs and does not replace them.

Use these docs as the local contract layer:

- `docs/architecture/data_architecture.md`
- `docs/architecture/data_model.md`
- `docs/business/data_sources_downloads_vs_api.md`
- `docs/business/downloaded_csv_contracts.md`
- `docs/business/api_contracts_market_public.md`
- `docs/standards/nlp-standards.md`
- `docs/standards/postgres-standard.md`
- `docs/standards/engineering_standards.md`

## Canonical Runtime Contract

- Repository name: `omnibid`
- Runtime/app name in env files: `app-chilecompra`
- Docker is the canonical runtime for database-backed work.
- Host `.env` is for local tools and uses `localhost:5432` for the main database and `localhost:5433` for the test database.
- `.env.docker` is for container execution and uses service DNS names such as `db` and `db_test`.
- `DATABASE_URL` and `TEST_DATABASE_URL` must remain separate.
- The current effective database image in Compose is `postgres:16-alpine`.

Do not silently rename the repo, the app name, or the runtime service names. If a rename is required, it needs its own proposal.

## Source Profiles

Treat the input source as one of the following profiles:

| Profile | Status | Contract |
| --- | --- | --- |
| `csv_drop` | Canonical now | Monthly CSV snapshots from ChileCompra Datos Abiertos, ingested as traceable files. |
| `api_json` | Documented future or parallel profile | Operational API queries with ticket-based access and query-oriented responses. |
| `open_data_snapshot` | Documented future or parallel profile | Historical download or snapshot material used for backfill, evidence, or comparative analysis. |

Rules:

- Do not mix source profiles silently.
- Do not map JSON API payloads to CSV drop semantics without an explicit adapter.
- Do not treat a human-facing portal as a machine contract unless a separate adapter documents the mapping.

## Deterministic Ingestion Contract

Current ingestion is CSV-driven and must remain fail-fast.

- Use `csv.DictReader` or `csv.reader` with an explicit delimiter and quote character.
- Keep file reads explicit about newline handling.
- Keep the canonical CSV delimiter as `;`.
- Keep the canonical file encoding as `latin1` for the current ChileCompra drops.
- Fail fast if required columns are missing.
- Keep dataset root resolution explicit with `pathlib.Path`.
- Keep CLI entrypoints explicit with `argparse`.
- Use `json` for profiling and state artifacts, with stable, UTF-8 output.

Current raw contracts require:

- file hash: SHA-256 of the file bytes
- row hash: SHA-256 of the canonical JSON payload
- lineage fields: `source_file_id`, `batch_id`, `raw_row_num`, `row_hash_sha256`

Current null handling normalizes values such as:

- empty strings
- `NA` / `N/A` / `NULL`
- sentinel dates such as `1900-01-01`

## Identity and Grain

The repository already defines the current business keys in code. This standard makes them explicit:

- buyer key: `CodigoUnidadCompra`
- supplier key: `codigo:<CodigoProveedor>` first, then `rut:<RutProveedor>`
- category key: `codigoCategoria`, with ONU fallback prefixed as `onu:`
- notice key: `CodigoExterno`
- purchase order key: `Codigo`
- purchase order line key: `Codigo` + `IDItem`
- notice line key: `CodigoExterno` + `Codigoitem` / `CodigoItem`

Rules:

- Do not aggregate raw rows as business entities before the grain is normalized.
- Do not invent a new identity key if a canonical business key already exists.
- Use unique constraints or equivalent database guarantees to enforce deduplication.

## Normalization and Text Handling

Current shared text cleaning uses the Python Unicode and string toolchain, not a hidden external framework.

- normalize text explicitly before feature extraction
- collapse whitespace explicitly
- remove accents only when the repository contract requires a derived clean copy
- keep the original business text in source-aligned fields
- keep date parsing explicit and UTC-aware when timestamps are converted or compared

The current shared cleaner uses Unicode decomposition plus combining-mark stripping. Do not switch this behavior casually; if a different normalization form is needed, it needs a proposal and tests.

## Database and Migration Contract

Use the official database stack in the repo, not ad hoc SQL strings.

- Pydantic Settings loads runtime configuration from `.env`
- SQLAlchemy 2.x is the ORM/core layer
- PostgreSQL `ON CONFLICT` semantics govern deterministic upserts
- Alembic is the schema source of truth

Rules:

- Every durable deduplication rule needs a unique constraint or equivalent.
- `ON CONFLICT DO UPDATE` or `DO NOTHING` must be tied to explicit conflict keys.
- Do not depend on implicit row order for correctness.
- Use numeric and datetime types intentionally; do not hide business amounts or dates in string columns.
- Keep schema changes inside migrations.

## Raw, Normalized, and Silver Rules

### Raw

- Raw is append-oriented and traceable.
- Raw keeps source metadata and row lineage.
- Raw is not the place for business aggregation.

### Normalized

- Normalized is canonical and query-ready.
- Normalized must preserve deterministic business keys.
- Normalized upserts must be explicit and conflict-key driven.

### Silver

- Silver is the canonical procurement-cycle layer.
- Silver may contain deterministic enrichments and semantic annotations.
- Silver must not contain predictive scores, probability fields, or dense vectors.
- Silver annotation tables are metadata-only and reference-only.
- `tfidf_artifact_ref` must remain a reference string beginning with `tfidf://`.

Current Silver annotation tables:

- `silver_notice_text_ann`
- `silver_notice_line_text_ann`
- `silver_purchase_order_line_text_ann`

Forbidden in Silver annotation payloads:

- serialized TF-IDF vectors or matrices
- dense embeddings
- prediction scores
- forecast outputs
- ad hoc model blobs

## NLP Boundary

Keep NLP deterministic and layered.

- spaCy is the canonical Spanish linguistic pipeline
- fastText is the offline language identification layer
- scikit-learn is the deterministic count / TF-IDF feature layer
- NLTK Snowball stemming is auxiliary only
- Sentence Transformers and Hugging Face pipelines are downstream-only

Rules:

- Keep Silver annotations metadata-only.
- Keep semantic inference and ranking out of Silver.
- Keep rule-based augmentation versioned.
- Keep the NLP version explicit in every Silver annotation row.

## Validation and Evidence

Validation is part of the contract, not an afterthought.

- Use unit tests for normalization, hashing, identity, and feature extraction contracts.
- Use database-backed tests when a change writes rows.
- Use Docker-first smoke checks for runtime validation.
- Record evidence in `docs/evidence/` when a contract, schema, or runtime behavior changes.
- Keep source notes in `docs/references/` so the next agent does not have to rediscover the same decisions.

## Official Sources Consulted

| Source | Topic | Decision |
| --- | --- | --- |
| https://docs.python.org/3/library/csv.html | CSV file reading and writing | Use explicit CSV dialects, `DictReader`, and file-level newline handling for the current CSV drop contract. |
| https://docs.python.org/3/library/hashlib.html | Secure hashes and message digests | Use SHA-256 for file and row identity hashes. |
| https://docs.python.org/3/library/pathlib.html | Filesystem paths | Use `Path` for dataset-root resolution and file discovery. |
| https://docs.python.org/3/library/argparse.html | CLI parsing | Keep operator scripts explicit and fail fast on missing inputs. |
| https://docs.python.org/3/library/json.html | JSON encoding/decoding | Use stable JSON artifacts for profiling, state, and evidence. |
| https://docs.python.org/3/library/datetime.html | Date and time handling | Treat runtime timestamps and comparisons explicitly, with UTC-aware handling when needed. |
| https://docs.python.org/3/library/unicodedata.html | Unicode normalization | Keep text normalization explicit and versioned. |
| https://docs.pydantic.dev/latest/concepts/pydantic_settings/ | Settings loading and `.env` precedence | Keep configuration environment-driven and separate host and Docker runtime files. |
| https://docs.sqlalchemy.org/en/20/dialects/postgresql.html | PostgreSQL insert/upsert support | Use SQLAlchemy PostgreSQL `insert()` with explicit conflict targets for deterministic upserts. |
| https://docs.sqlalchemy.org/en/20/orm/session_api.html | Session and transaction API | Keep write paths transaction-aware and batch-isolated. |
| https://alembic.sqlalchemy.org/en/latest/ | Migration environment and revision flow | Keep schema changes migration-backed and reviewable. |
| https://www.postgresql.org/docs/16/sql-insert.html | `INSERT` and `ON CONFLICT` | Treat PostgreSQL upsert semantics as the database authority for deduplication. |
| https://www.postgresql.org/docs/16/datatype-numeric.html | Numeric types | Use precise numeric types for amounts and quantities. |
| https://spacy.io/api/language/ | Pipeline orchestration | Use registered spaCy pipelines and components for deterministic text processing. |
| https://spacy.io/api/entityruler | Rule-based entity augmentation | Allow versioned rule-based augmentation when deterministic matching is safer. |
| https://spacy.io/models/es/ | Spanish model families | Use the official Spanish model family guidance when choosing the canonical Spanish pipeline. |
| https://fasttext.cc/docs/en/language-identification | Language identification | Use UTF-8 normalized text for offline language identification. |
| https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.CountVectorizer.html | Count-based lexical features | Use deterministic count and n-gram extraction for lexical features. |
| https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html | TF-IDF feature extraction | Use reference-only TF-IDF artifacts, not vector persistence in Silver. |
| https://www.nltk.org/api/nltk.stem.SnowballStemmer.html | Spanish stemming | Keep stemming auxiliary only. |
| https://sbert.net/docs/sentence_transformer/usage/usage.html | Embeddings and semantic search | Keep embeddings downstream of Silver. |
| https://huggingface.co/docs/tokenizers/pipeline | Tokenization pipeline stages | Treat subword tokenization as a separate downstream branch. |
| https://huggingface.co/docs/transformers/main_classes/pipelines | Transformer inference pipelines | Keep token classification and feature extraction outside Silver. |
| https://www.chilecompra.cl/datos-abiertos/ | Datos Abiertos overview | Treat open-data downloads as a historical / analytical source profile. |
| https://www.chilecompra.cl/api/ | API overview | Treat the Mercado Publico API as operational and query-oriented. |
| https://www.mercadopublico.cl/Home/Contenidos/QueEsLicitacion | Licitacion definition | Keep tender terminology aligned to the official platform semantics. |
| https://www.mercadopublico.cl/Home/ | Mercado Publico home | Treat the public portal as a human-facing operational surface with frequently refreshed data. |

## Notes

- The current repository implementation still uses CSV drops as the canonical source profile.
- `api_json` and `open_data_snapshot` are documented contracts for the next implementation slice, not silent defaults.
- The effective database runtime in Compose is PostgreSQL 16, so all documentation and proposals should align to that runtime until Compose changes.

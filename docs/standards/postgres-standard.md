# PostgreSQL Standard: Schema, Security, Migrations, Indexing, and Extension Governance

## Overview

This project uses PostgreSQL as the canonical persistence layer for source documents, canonical records, ledger events, and future market-data storage.

This standard defines how PostgreSQL should be used in this repository so schema changes remain:

- deterministic
- auditable
- performance-aware
- compatible with the ledger-first architecture

## Scope

This standard applies to:

- SQLAlchemy models
- Alembic migrations
- PostgreSQL security posture
- PostgreSQL-specific query patterns
- indexes and constraints
- extension adoption decisions
- database performance investigation workflows

This standard does not replace product decisions or implementation guides. It defines the baseline rules the repository must follow.

## Version Baseline

- Local development baseline: PostgreSQL 18
- Reference runtime in Docker Compose: `postgres:18-alpine`
- Official PostgreSQL documentation is the primary authority

When older PostgreSQL documentation is referenced for background reading, it must not override behavior verified against the current project baseline.

## Source Priority

Use sources in this order:

1. Official PostgreSQL documentation
2. Official extension documentation such as `pgvector` or Tiger Data / TimescaleDB docs
3. Repository code and migrations
4. Secondary articles or blog posts for ideas only

Do not turn a blog optimization tip into a repository rule without validating it against:

- actual query patterns
- actual table sizes
- `EXPLAIN` evidence
- the current PostgreSQL version

## Repository Context

Current repository usage is ledger-first and idempotency-first.

Examples already implemented:

- `source_document.sha256` is the document-level deduplication key
- `canonical_pdf_record.fingerprint` is the transaction-level deduplication key
- canonical records and derived ledger rows are stored separately
- JSON payloads are retained for auditability, but important query fields are surfaced as typed columns

These choices should remain stable unless a deliberate architectural decision changes them.

Current runtime posture is local development first. That does not remove the need to document secure defaults. It means the documentation must distinguish clearly between:

- local development defaults
- stronger remote, shared, or production-facing controls

## Security Baseline

### Principle of least privilege

- Application connections should use the narrowest role that can perform the required work.
- Do not run the application as a PostgreSQL superuser outside short-lived setup or admin tasks.
- Grant only the privileges actually required on schemas, tables, sequences, and functions.
- Prefer role-based access control over sharing a single broad database account.

### Network exposure

- Default to local-only exposure unless remote access is required.
- Restrict `listen_addresses` intentionally when the database is not meant to be network-accessible.
- Restrict client sources with `pg_hba.conf`.
- Do not leave broad trusted network rules in place after temporary debugging.

### Authentication

- Prefer `scram-sha-256` for password-based authentication.
- Treat `md5` as legacy compatibility only.
- Avoid `password` authentication on untrusted networks.
- Never rely on `trust` authentication outside tightly scoped local-development scenarios.

### Encryption

- Require TLS for remote or shared-environment connections.
- Treat local Docker-only development as a lower-security exception, not the default model for all environments.
- If sensitive columns eventually require application-visible encryption-at-rest behavior, document the exact design instead of assuming PostgreSQL storage alone is enough.

### Secrets handling

- Keep database credentials in environment configuration, not committed source files.
- Do not log raw credentials or full connection strings.
- Rotate credentials explicitly when environments or operators change.

### Schema and privilege hygiene

- Review privileges granted to `PUBLIC`.
- In multi-role environments, strongly consider revoking `CREATE` on schema `public` from `PUBLIC`.
- Use explicit schema ownership and grants instead of relying on permissive defaults.
- Be careful with `SECURITY DEFINER`, views used as security boundaries, and unsafe `search_path` assumptions.

### Auditing and logging

- Keep enough database and application logging to investigate failed authentication, privilege mistakes, and destructive changes.
- When audit requirements grow, define them explicitly instead of assuming generic logs are sufficient.
- Treat periodic privilege and connection-policy review as part of database maintenance.

## Schema Design Rules

### Model the query surface explicitly

- Use typed relational columns for fields that will be filtered, joined, sorted, grouped, or constrained.
- Use JSON for audit payloads, provenance, or infrequently queried derived blobs.
- Do not hide core business fields inside JSON if they are part of the stable query surface.

### Prefer explicit integrity over application-only assumptions

- Every durable relationship should use foreign keys unless there is a documented reason not to.
- Every deduplication rule should be enforced with a unique constraint or equivalent database-level guarantee.
- Nullability must reflect actual business rules, not convenience.

### Keep ledger truth separate from derived outputs

- Canonical transaction records are system-of-record inputs.
- Ledger rows, lots, and lot dispositions are derived durable tables.
- Market data, quote history, and future analytics snapshots must remain separate from the transaction ledger.

### Use precise data types

- Use `NUMERIC` for money and share quantities that require exact decimal behavior.
- Use `DATE` or timezone-aware timestamps intentionally based on the domain meaning.
- Use bounded `VARCHAR` or `TEXT` based on semantics, not habit.

## Migration Rules

### All schema changes go through Alembic

- Do not apply manual production schema drift outside migrations.
- Autogenerated migrations must be reviewed and edited when needed.
- A migration is not complete until indexes, constraints, and downgrade posture have been reviewed.

### Migrations must preserve fail-fast behavior

- Required tables, constraints, and extensions must be created explicitly.
- Do not introduce silent fallback behavior when required database features are absent.
- If an extension is required for a feature, installation and enablement must be explicit.
- Security-sensitive privilege changes must be explicit and reviewable.

### Use additive-first evolution where practical

- Prefer additive changes before destructive ones.
- If data migration is required, keep schema migration and data backfill logic understandable and auditable.
- Destructive changes must be justified and sequenced carefully.

## Constraint Standard

- Primary keys are required on all durable tables.
- Unique constraints are required for deterministic deduplication keys.
- Foreign keys should usually use explicit `ondelete` behavior.
- Do not create duplicate indexes that repeat what a primary key or unique constraint already provides.

## Role And Privilege Standard

- Distinguish owner/admin roles from application runtime roles when the environment becomes shared or remotely accessible.
- Use `GRANT` and `ALTER DEFAULT PRIVILEGES` intentionally; do not rely on permissive defaults.
- Review schema privileges in addition to table privileges.
- Prefer ownership and grant models that remain understandable during migrations and incident review.
- Avoid broad `ALL PRIVILEGES` grants unless they are truly justified and documented.

## Indexing Standard

### Start from query patterns

An index is justified when it supports an actual access pattern such as:

- `WHERE`
- `JOIN`
- `ORDER BY`
- `GROUP BY`
- uniqueness enforcement

Do not add indexes because a column "seems important."

### Preferred index types

- Use B-tree indexes by default.
- Use multicolumn indexes when a real query filters or sorts across multiple columns in a stable order.
- Use partial indexes when only a small, repeatedly queried subset matters.
- Use expression indexes only for stable immutable expressions.
- Use `INCLUDE` columns only when an actual read pattern benefits from index-only scans.
- Use BRIN only for very large append-ordered tables where physical locality matters.

### Repository-specific guidance

Current query shapes suggest future evaluation of multicolumn indexes such as:

- canonical records by `source_document_id, event_date, id`
- portfolio transactions by `source_document_id, event_date, id`
- corporate actions by `source_document_id, event_date, id`

These are candidates, not automatic requirements. Add them only after plan evidence shows the current single-column indexes are insufficient.

### Index review checklist

Before adding an index, answer:

- Which exact query is slow?
- What is the current `EXPLAIN (ANALYZE, BUFFERS)` plan?
- What selectivity does the indexed predicate have?
- Does an existing index already cover the access pattern?
- What write amplification and storage cost does the new index add?

## Query and Performance Investigation Standard

### Default workflow

1. Capture the real query.
2. Run `EXPLAIN`.
3. Run `EXPLAIN ANALYZE`.
4. Run `EXPLAIN (ANALYZE, BUFFERS)` for deeper investigation.
5. Change one variable at a time.
6. Re-measure.

### What to inspect first

- sequential scans on large tables
- sort nodes on large result sets
- repeated heap fetches
- nested loops on unexpectedly large joins
- bad row-count estimates
- unnecessary repeated queries at the application layer

### Observability baseline

When performance work begins to matter, prefer enabling and using:

- `pg_stat_statements`
- query plan inspection via `EXPLAIN`
- autovacuum and analyze health checks

Do not begin with global memory tuning or obscure planner flags before understanding the workload.

## Write Path Standard

- Prefer transactional batches over many tiny commits.
- Use PostgreSQL-native upsert or conflict handling when idempotency is required.
- Keep deduplication logic anchored to deterministic business keys.
- Avoid row-by-row persistence loops for large ingest workloads once profiling shows batch operations are needed.

The current persistence code uses conflict-aware inserts correctly for deduplicated source documents and canonical records. Future bulk ingestion should preserve those guarantees.

## JSON and JSONB Guidance

- Keep JSON payloads for audit trails, raw records, and provenance where schema flexibility is useful.
- Surface stable filter and sort fields into typed columns.
- Do not treat JSON as a substitute for relational modeling.
- Add GIN or expression indexes on JSON content only when a real query pattern justifies them.

## Maintenance Standard

- Trust autovacuum as the baseline, but verify it is keeping up when tables grow.
- Use `ANALYZE` or wait for autovacuum analyze after major data-shape changes if plans are clearly stale.
- Watch for table bloat and dead tuples before blaming PostgreSQL itself.
- Benchmark representative data volumes, not toy examples, before making structural tuning changes.

## Extension Governance

### General rule

An extension is adopted only when:

- it supports a concrete product or platform requirement
- native PostgreSQL is not the simpler sufficient option
- installation, migration, local development, and rollback implications are understood

### Enablement rule

Using an extension requires two distinct steps:

1. install the extension binaries in the PostgreSQL runtime
2. enable it in the database with `CREATE EXTENSION`

The stock `postgres:18-alpine` image does not imply that optional extensions such as `pgvector` or TimescaleDB are available.

### Current extension posture

- `pgvector`: optional future extension for embeddings and vector similarity search
- `TimescaleDB`: optional future extension for large append-heavy time-series workloads such as `price_history`

Neither extension is part of the current repository baseline.

## Security Features To Use Carefully

- `SECURITY DEFINER` functions and procedures
- views intended as security boundaries
- row-level security
- predefined roles with elevated power
- extensions that add cryptographic, network, or audit capabilities

These features are useful, but they change the security model and should be introduced only with explicit design and review.

## When To Use Native PostgreSQL First

Choose native PostgreSQL first for:

- canonical records
- document metadata
- import jobs
- ledger events
- lots and lot dispositions
- moderate-sized market data tables
- deterministic analytics queries that standard indexes can support

Do not adopt extensions just because the domain is finance or because data contains dates.

## Anti-Patterns

- adding indexes without plan evidence
- duplicating indexes created implicitly by unique constraints
- storing core query fields only inside JSON
- running the application with superuser privileges
- using `trust` authentication beyond tightly controlled local development
- committing database credentials or connection strings with secrets
- relying on default `PUBLIC` privileges without review
- using `SECURITY DEFINER` or security-boundary views without explicit threat review
- using time-series extensions for ledger truth tables
- using vector extensions before the product has embeddings or semantic retrieval requirements
- making global tuning changes before understanding the specific slow query
- prematurely partitioning tables that are still small

## Validation Commands

Use these commands when validating schema or migration work:

```bash
docker-compose up -d db
uv run alembic upgrade head
uv run pytest -v -m integration
```

Use these commands when investigating a performance issue manually:

```sql
EXPLAIN SELECT ...;
EXPLAIN ANALYZE SELECT ...;
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;
```

## References

- PostgreSQL 18 docs: https://www.postgresql.org/docs/18/
- PostgreSQL indexes: https://www.postgresql.org/docs/18/indexes.html
- PostgreSQL multicolumn indexes: https://www.postgresql.org/docs/18/indexes-multicolumn.html
- PostgreSQL `CREATE INDEX`: https://www.postgresql.org/docs/18/sql-createindex.html
- PostgreSQL `EXPLAIN`: https://www.postgresql.org/docs/18/using-explain.html
- PostgreSQL `CREATE EXTENSION`: https://www.postgresql.org/docs/18/sql-createextension.html
- PostgreSQL routine vacuuming: https://www.postgresql.org/docs/18/routine-vacuuming.html
- PostgreSQL client authentication: https://www.postgresql.org/docs/18/client-authentication.html
- PostgreSQL `pg_hba.conf`: https://www.postgresql.org/docs/18/auth-pg-hba-conf.html
- PostgreSQL password authentication: https://www.postgresql.org/docs/18/auth-password.html
- PostgreSQL roles: https://www.postgresql.org/docs/18/user-manag.html
- PostgreSQL `GRANT`: https://www.postgresql.org/docs/18/sql-grant.html
- PostgreSQL default privileges: https://www.postgresql.org/docs/18/sql-alterdefaultprivileges.html
- PostgreSQL schemas and privileges: https://www.postgresql.org/docs/18/ddl-schemas.html
- PostgreSQL function security: https://www.postgresql.org/docs/18/perm-functions.html

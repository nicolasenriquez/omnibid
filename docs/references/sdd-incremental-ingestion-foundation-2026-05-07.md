# SDD: Incremental Ingestion Foundation

## Decision

Use Postgres row-level locking as the queue claim primitive for the shared ingestion substrate.

The queue claim path should use `SELECT ... FOR UPDATE SKIP LOCKED` so multiple workers can safely race over the same job table without double-claiming the same row.

Claim order must be deterministic:

- `priority ASC`
- `available_at ASC`
- `created_at ASC`
- `id ASC`

Advisory locks can remain a later option for coarse-grained mutual exclusion, but they are not needed for the basic claim path.

## Verified Official Sources

1. PostgreSQL SELECT documentation
   - https://www.postgresql.org/docs/current/sql-select.html
   - Confirms `FOR UPDATE` locking clauses and `SKIP LOCKED` for queue-like tables.
2. PostgreSQL Explicit Locking documentation
   - https://www.postgresql.org/docs/current/explicit-locking.html
   - Confirms row-level locking and advisory locks as separate primitives.
3. PostgreSQL NOTIFY documentation
   - https://www.postgresql.org/docs/current/sql-notify.html
   - Reference only for possible later wake-up mechanisms, not required in this slice.

## Scope Note

This note covers the queue substrate only.

Raw strict dedupe, scoped normalization, Mercado Público API ingestion, and Silver refresh stay in follow-on proposals.

## Problem

The repository already has the contracts needed for procurement analytics, but they are split across business docs, standards, runtime config, and pipeline code. That makes it easy for a future implementation slice to drift into mixed source profiles, stale PostgreSQL assumptions, or unclear Silver semantics.

The repository also has a real runtime split that needs to stay explicit:

- host `.env` uses localhost database URLs
- Docker `.env.docker` uses service DNS names
- Compose currently runs PostgreSQL 16
- `TEST_DATABASE_URL` must remain separate from `DATABASE_URL`

## Design Goals

1. Make the customer analytics contract discoverable from one standard.
2. Keep the current CSV drop pipeline canonical until a future adapter change is approved.
3. Keep the docs aligned with the real Docker/runtime baseline.
4. Preserve the Silver metadata-only / reference-only boundary.
5. Add code-level guardrails for source-profile routing and runtime validation without introducing a broad refactor.

## Proposed Architecture

```text
docs/standards/customer-analytics-standards.md
  -> source profiles
  -> runtime and env contract
  -> deterministic ingestion contract
  -> identity and grain
  -> Silver boundary
  -> validation and evidence

docs/references/sdd-customer-analytics-standards-2026-05-05.md
  -> official source URLs
  -> repository context
  -> implementation notes

docs/references/sdd-official-sources-registry.md
  -> official docs registry used by future agents

backend/pipeline/
  -> explicit source-profile routing helpers
  -> canonical orchestration wrappers
  -> runtime contract checks for DB-backed work

backend/core/config.py
  -> environment loading and fail-fast DB/runtime validation

tests/unit/
  -> pipeline routing, env validation, and contract tests

docs/standards/postgres-standard.md
  -> effective PostgreSQL runtime baseline
```

## Contract Boundaries

### Source profiles

- `csv_drop` is the only implemented profile in the current pipeline.
- `api_json` is documented as an operational profile for a later slice.
- `open_data_snapshot` is documented as a historical/profiled source for backfill or evidence.
- Code must not silently treat those profiles as interchangeable.

### Runtime and DB

- Keep Docker as the canonical runtime for DB-backed work.
- Keep host and Docker env files separate.
- Keep the current Compose PostgreSQL 16 baseline documented.
- Fail fast when the runtime contract is missing or inconsistent.

### Silver and NLP

- Keep Silver metadata-only and reference-only.
- Keep `tfidf_artifact_ref` as a `tfidf://...` reference string.
- Keep embeddings, scores, and forecasts downstream only.

## Alternatives Considered

1. Leave the new standard undocumented and rely on existing scattered docs.
   - Rejected because the current split is already causing drift and ambiguity.
2. Rewrite the pipeline before documenting the contract.
   - Rejected because the repo already has a working pipeline and the immediate gap is the contract surface.
3. Treat the Mercado Publico API as the canonical profile immediately.
   - Rejected because the current implementation is CSV-first and the API path needs its own proposal.
4. Ignore the Compose PostgreSQL version mismatch.
   - Rejected because the runtime baseline needs to be explicit before any future schema work.

## Risks

- Future agents may still treat the API and CSV profiles as interchangeable unless the docs and code remain explicit.
- If the Compose baseline changes again without doc updates, the standard will drift.
- If the pipeline grows new code paths without tests, the runtime contract could regress silently.
- If a later implementation slice persists new NLP fields in Silver, the boundary will need a follow-up migration-backed change.

## Mitigations

- keep the source profiles table front and center
- keep the runtime contract in the standard rather than hiding it in notes
- keep the SDD note tied to official sources and repo context
- add focused unit tests around pipeline routing and env validation
- update the PostgreSQL standard when the Compose runtime changes

## Migration Considerations

This slice should stay schema-neutral.

If a later change adds API ingestion adapters, a runtime rename, or new Silver fields, those should be separate proposals with explicit migration review.

## Validation Plan

- read the official source pages and confirm the URLs in the registry
- review the env files and Compose runtime together
- confirm the standard points to the current implemented pipeline rather than a hypothetical one
- confirm pipeline routing and runtime validation fail fast on unsupported or inconsistent inputs
- keep the first slice additive and low-risk

## Open Questions

None.

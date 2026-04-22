# Product Vision

Build the data backbone for Chile public procurement intelligence.

## Phase 1 Goal
Create a deterministic historical batch pipeline with:
- auditability
- observability
- idempotent loads
- schema discipline

## Delivery Strategy (Stage-Gated)

Phase 1 is executed with controlled gates:

1. Bronze/Raw ingestion foundation
2. Bronze/Raw reliability and data-quality hardening
3. Silver/Normalized core canonicalization
4. Silver/Normalized domain modeling expansion
5. Gold business layer implementation

Gold is intentionally deferred until the normalized layer is operationally trusted.

## Current Hardening Priorities (Post Telemetry Reconciliation)

Before domain expansion and Gold work, execution should follow this sequence:

1. Transaction consistency hardening in ETL scripts:
   - explicit rollback behavior after SQL failures
   - deterministic failure-state persistence
2. Schema/metadata parity hardening:
   - align ORM metadata with migrated indexes/constraints
   - prevent autogenerate drift and hidden schema assumptions
3. Operational quality gates:
   - persist normalized data-quality issues
   - enforce threshold-based fail/warn rules per run
4. Operational API guardrails:
   - bounded list endpoint limits
   - non-expensive dataset summary strategy for large tables

Only after those gates are stable should the roadmap move to normalized domain expansion.

## Not in Phase 1
- Full user app
- Advanced recommendation engine
- Agent orchestration in critical path

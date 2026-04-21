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

## Not in Phase 1
- Full user app
- Advanced recommendation engine
- Agent orchestration in critical path

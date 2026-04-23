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
5. Silver procurement-cycle canonicalization + deterministic feature foundations
6. Gold business layer implementation

Gold is intentionally deferred until the normalized layer is operationally trusted.

## Current Priorities (Post Domain-Entity Expansion)

Before Gold work, execution should follow this sequence:

1. Expand Silver to canonical procurement process entities:
   - notice -> line -> bid -> award -> purchase order -> purchase-order line
2. Complete explicit master and bridge contracts:
   - organizations, units, supplier registry, category reference
   - optional notice-to-OC link and supplier participation bridge
3. Add deterministic feature foundations in Silver:
   - temporal, structural, competition, and materialization derivations
4. Add versioned semantic annotation contracts:
   - annotation-only semantics (no business prediction outputs)

Only after these gates are stable should the roadmap move to Gold outputs and predictive business layers.

## Not in Phase 1
- Full user app
- Advanced recommendation engine
- Agent orchestration in critical path

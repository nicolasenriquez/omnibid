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

## Current Priorities

The Silver procurement-cycle foundation is implemented. Current execution is focused on read-only workspace slices over trusted Silver facts:

1. Keep Silver canonical procurement process entities stable:
   - notice -> line -> bid -> award -> purchase order -> purchase-order line
2. Serve read-only investigation and opportunity workflows from Silver-first contracts.
3. Use Normalized joins only for documented display fields currently absent from Silver.
4. Keep deterministic feature foundations and versioned semantic annotations in Silver.
5. Keep predictive scoring, forecasting, recommendations, and anomaly verdicts out of Silver and out of the current read-only MVP.

Only after these gates are stable should the roadmap move to Gold outputs and predictive business layers.

## Opportunity Workspace MVP

The next UI-facing product slice is a read-only Opportunity Workspace for deciding which public procurement opportunities deserve investigation.

Primary workflow:
- search and filter licitaciones.
- scan deterministic stages in Radar.
- inspect parent opportunities in Explorer.
- open detail without losing list or board context.
- review products/services, buyer, timeline, economic evidence, offers, awards, and purchase-order evidence where supported by data.

MVP boundaries:
- one Radar card or Explorer parent row represents one licitación/notice.
- child lines, offers, awards, and purchase orders remain detail or expanded-row evidence, not list grain.
- all user-facing UI labels are Spanish.
- no AI score, recommendation, assignment, discard, notes, reminders, or editable workflow writes are implemented in the MVP.
- uncertain line-to-purchase-order relationships must show relationship certainty.
- current frontend path is `client/app/licitaciones/page.tsx`.
- current backend read API path is `backend/api/routers/opportunities.py`.

## Procurement Investigation Workspace

The procurement line investigation API is a read-only analyst/agent handoff slice:

- one summary per `notice_id + item_code`
- offer evidence before narrative context
- purchase-order-line evidence with match reason and certainty
- bounded context export for downstream review

It is not a scoring layer. Agent-generated narrative and predictive business conclusions must remain outside canonical data.

## Not in Phase 1
- Full user app
- Advanced recommendation engine
- Agent orchestration in critical path

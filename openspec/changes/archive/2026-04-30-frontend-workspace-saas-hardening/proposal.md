## Why

The repository now has read-only opportunity APIs and a Next.js Opportunity Workspace path, but the frontend needs a stronger product-grade UI contract before implementation continues. The product direction calls for a Spanish, read-only workspace where users can search, filter, scan deterministic opportunity stages, inspect one notice at a time, and review evidence without losing context.

The requested visual direction uses SaaS premium workspace references: a calm operational shell, compact tabs, pulse metrics, focused filters, a dense Explorer table, a Radar Kanban, and a right-side detail panel. This proposal turns that visual reference into explicit frontend requirements so implementation can harden the UI without copying the reference app, overbuilding future workflow features, or leaking technical backend field names into the user experience.

## What Changes

- Harden the Opportunity Workspace frontend around two primary views:
  - `Explorador`: a hierarchical table where one parent row represents one licitación/notice.
  - `Radar`: a Kanban-style board grouped by derived opportunity stage.
- Add a SaaS premium operational shell and composition:
  - Spanish labels.
  - workspace header or home summary.
  - `Pulso de oportunidades`.
  - focused filters with active-filter state.
  - detail drawer that preserves list/board context.
- Define evidence-oriented interactions:
  - row/card selection opens the same licitación detail panel.
  - table expansion shows notice lines, offers, awards, and purchase-order evidence only when available.
  - uncertain line-to-purchase-order relationships show certainty instead of being rendered as fact.
- Add frontend hardening requirements:
  - typed API DTO to view-model mapping.
  - loading, empty, error, hover, selected, focus, and responsive states.
  - no fake data and no visible raw technical field names.
- Keep the MVP read-only and out of future workflow scope:
  - no AI analysis.
  - no recommendations or scores.
  - no assignment, notes, discard, reminders, editable workflow, or persistent drag-and-drop.

## Capabilities

### New Capabilities

- `opportunity-workspace-premium-frontend`: Spanish read-only SaaS workspace UI for Explorer, Radar, filters, pulse metrics, detail drawer, evidence states, and frontend resilience.

### Modified Capabilities

None.

## Impact

- Affected implementation areas:
  - `client/app/licitaciones/`
  - `client/src/features/opportunity-workspace/`
  - `client/src/lib/api/`
  - frontend styling/theme files under `client/`
- Affected contracts:
  - frontend view models derived from `/opportunities`
  - display mapping for opportunity stages, official states, relationship certainty, and evidence sections
- Documentation impact:
  - product/frontend notes may need to reflect final UI terminology and MVP boundaries.
- Operational impact:
  - frontend validation should use the local Next.js workspace with backend served through the Docker-first runtime when backend data is needed.

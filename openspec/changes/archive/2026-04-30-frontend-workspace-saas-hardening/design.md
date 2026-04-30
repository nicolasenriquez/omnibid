## Context

The repository has a Silver-first read API and a Next.js Opportunity Workspace at `/licitaciones`. The product vision defines the current UI-facing slice as a read-only workspace for searching, filtering, scanning deterministic stages, inspecting parent opportunities, and reviewing evidence.

The user supplied visual references for a SaaS premium workflow application. The references should inform composition, density, hierarchy, and interaction quality, but must not be copied literally or imported as a different domain model.

## Goals / Non-Goals

**Goals**
- Make the Opportunity Workspace feel like a premium operational SaaS product.
- Preserve a read-only MVP boundary.
- Use Spanish user-facing labels throughout the workspace.
- Keep one parent Explorer row and one Radar card per licitación/notice.
- Show child lines, offers, awards, and purchase-order evidence as detail or expanded evidence.
- Preserve context by using a right-side detail drawer for selected rows/cards.
- Harden view-model mapping, loading states, empty states, error states, keyboard focus, and responsive behavior.

**Non-Goals**
- Copy the reference UI literally.
- Implement AI analysis, recommendations, opportunity scores, assignments, notes, reminders, discard actions, or workflow mutations.
- Implement persistent drag-and-drop in Radar.
- Add new backend write APIs.
- Introduce Gold or predictive business outputs.
- Replace backend contracts unless the current API cannot support a required read-only display field.

## Decisions

1. **Use `Explorador` and `Radar` as the primary workspace tabs.**
   - Rationale: `Explorador` communicates an analytical table, not a raw database grid; `Radar` communicates stage scanning without implying editable workflow.

2. **Keep one licitación/notice as the list and board grain.**
   - Rationale: the product boundary says child lines, offers, awards, and purchase orders are evidence, not parent list entities.

3. **Map backend DTOs into semantic frontend view models before rendering.**
   - Rationale: components should render domain concepts and Spanish labels, not raw database or API field names.

4. **Use a shared detail drawer for Explorer and Radar selection.**
   - Rationale: users should inspect a licitación without losing table or board context.

5. **Treat line-to-purchase-order relationships as evidence with certainty.**
   - Rationale: approximate or indirect matches must not be presented as canonical truth.

6. **Keep the visual system restrained and operational.**
   - Rationale: SaaS premium quality here means consistent spacing, typography, contrast, surfaces, state design, and density, not decorative gradients or marketing visuals.

7. **Defer full-screen detail and editable workflows.**
   - Rationale: a drawer-first MVP covers the primary desktop workflow while avoiding scope expansion.

8. **Validate with frontend-local checks plus real runtime smoke where feasible.**
   - Rationale: this is frontend-only work, but backend data should come from the canonical Docker-first runtime when integration validation is needed.

## Proposed UX Structure

Primary route:
- `/licitaciones`

Main composition:
- workspace shell with compact navigation and header.
- optional operational hero/summary section for last update and snapshot metrics.
- `Pulso de oportunidades` with stage counts and quick filters.
- filter workspace with primary filters always visible and advanced filters progressive.
- tab switcher:
  - `Explorador`
  - `Radar`
- selected licitación detail drawer.

Explorer table:
- one parent row per licitación.
- parent columns for code, name, buyer, category, region, official state, stage, amount, closing date, days remaining, line count, offer count, and purchase-order evidence count where available.
- expandable row section for lines/items, offers, awards, purchase orders, and certainty.

Radar board:
- columns by derived stage:
  - Abiertas
  - Cierra pronto
  - Cerradas
  - Adjudicadas
  - Revocadas o suspendidas
  - Sin clasificar
- cards show only scan-critical information.
- clicking a card opens the shared detail drawer.

Detail drawer:
- header with code, title, official state, stage, next milestone, and amount.
- sections for summary, key dates, buyer, products/services, amounts, offers, awards, purchase orders, certainty, and metadata.
- MVP actions limited to copy code, open licitación, and view full detail if already supported.

## Visual Quality Bar

The implementation should include:
- clear tab active state.
- compact chips with consistent color semantics.
- subtle borders and shadows.
- strong selected-row/card state.
- accessible visible focus.
- skeleton loading.
- useful empty states.
- actionable error states.
- tooltips or accessible full-text affordances for truncation.
- responsive layout that remains usable on mobile, even if desktop-first.

Avoid:
- fake data.
- emojis.
- low-contrast gray text.
- excessive chips.
- nested cards without purpose.
- saturated gradients or heavy shadows.
- visible labels like `derivedStage`, `externalNoticeCode`, `Issue`, or `Kanban`.

## Risks / Trade-offs

- **[Risk] Premium UI polish expands into broad redesign.**
  - Mitigation: keep implementation task-scoped around the existing `/licitaciones` workspace and MVP interactions.

- **[Risk] API shape may not expose all desired evidence in one response.**
  - Mitigation: start by auditing existing `/opportunities` summary/list/detail contracts and map only supported evidence; document gaps rather than inventing data.

- **[Risk] Table density can harm accessibility and mobile behavior.**
  - Mitigation: use responsive column priority, drawer/full-screen mobile behavior, visible focus, and readable contrast.

- **[Risk] Radar columns may imply editable workflow.**
  - Mitigation: keep drag-and-drop non-persistent or absent; stage is derived/read-only.

## Migration Plan

1. Audit current frontend files, API client contracts, and route behavior.
2. Freeze view-model and label mapping for the workspace.
3. Build visual shell, tabs, pulse metrics, filters, and shared UI primitives.
4. Harden Explorer table and hierarchical expansion.
5. Implement shared detail drawer.
6. Implement Radar board using the same selection/detail contract.
7. Add loading, empty, error, focus, hover, selected, and responsive states.
8. Validate frontend behavior against available API data and document any backend display gaps.

Rollback strategy:
- Keep changes localized to `client/`.
- Preserve existing API contracts.
- Prefer component-level refactors and route-level composition changes over backend changes.
- If a UI subsection is risky, feature it behind local component composition rather than changing data contracts.

## Open Questions

None.

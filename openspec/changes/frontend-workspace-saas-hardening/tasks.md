## 1. Frontend Baseline and Contract Audit

- [x] 1.1 Inspect the current `client/` structure, `/licitaciones` route, opportunity API client, view models, and styling approach.
  Notes: do not overwrite untracked generated artifacts under `client/.next` or `client/node_modules`.
  Notes: audit scope is `client/app/licitaciones/page.tsx`, `client/src/features/opportunity-workspace/workspace.tsx`, `client/src/types/opportunities.ts`, `client/src/lib/api/opportunities.ts`, `client/src/lib/url-state/workspace.ts`, `client/src/lib/formatters/opportunities.ts`, `client/src/components/ui/*`, and `client/src/styles/*`.
  Notes: implementation plan is to keep `/licitaciones` route composition in `workspace.tsx`, keep API DTOs in `types/opportunities.ts`, keep request/query mapping in `lib/api` and `lib/url-state`, and change UI hardening through shared components/styles plus explicit display contracts.
  Acceptance: implementation plan identifies the exact components and contracts to change before code edits.
- [x] 1.2 Freeze the Spanish label and stage mapping contract for user-visible UI.
  Notes: Spanish display labels are centralized in `client/src/features/opportunity-workspace/display-contract.ts`; raw DTO fields remain internal TypeScript contract names only.
  Notes: internal TypeScript names may stay in English; rendered labels must be Spanish.
  Acceptance: no raw field names such as `derivedStage` or `externalNoticeCode` appear in user-visible UI.

## 2. SaaS Workspace Shell and Navigation

- [x] 2.1 Build or refine the `/licitaciones` workspace shell with premium operational visual hierarchy.
  Notes: use restrained surfaces, borders, spacing, typography, and contrast; avoid marketing-style hero treatment.
  Notes: shell now uses a compact operational header with read-only status, API/filter state, result count, and responsive summary cells rather than a marketing hero.
  Acceptance: shell supports desktop-first use and does not break on narrow screens.
- [x] 2.2 Add or refine the `Explorador` / `Radar` tab switcher.
  Notes: the active tab must have clear visual state, accessible focus, and no English UI labels.
  Notes: tab switching preserves current filters and selected licitacion context by changing only the active view and page.
  Acceptance: switching views preserves applicable filter and selected-opportunity context where practical.

## 3. Pulse Metrics and Filters

- [x] 3.1 Implement `Pulso de oportunidades` from available summary/stage counts.
  Notes: chips may act as quick filters if current state management supports it.
  Notes: pulse metrics now render only from `/opportunities/summary`; loading/error/missing summary states stay explicit and do not derive fake totals from the current page.
  Acceptance: counts are API-backed or gracefully unavailable; no fake numbers are rendered.
- [x] 3.2 Harden the filter workspace.
  Notes: primary filters should be visible; advanced filters should be progressive and not crowd the first view.
  Notes: primary filters stay visible; page size, date ranges, amount, and UTM filter live in a progressive advanced block, while active filter chips and `Limpiar filtros` reset the supported URL state.
  Acceptance: active filter state is visible and `Limpiar filtros` reliably resets supported filters.

## 4. Explorer Table

- [x] 4.1 Render the Explorer as one parent row per licitación/notice.
  Notes: parent rows must not duplicate licitaciones by line, offer, supplier, or purchase-order evidence.
  Notes: Explorer defensively deduplicates API list rows by `noticeId` before rendering parent rows.
  Acceptance: list grain is visibly and structurally one row per notice.
- [x] 4.2 Add hierarchical expansion for child evidence.
  Notes: show lines/items, offers, awards, and purchase-order evidence only when supported by API data.
  Notes: expanded rows show supported list-level evidence counts and mark relationship certainty as `No confirmada`; full child evidence remains in the detail API path.
  Acceptance: uncertainty is shown with relationship certainty labels instead of being implied as fact.
- [x] 4.3 Add table interaction hardening.
  Notes: include selected row state, hover state, focus state, truncation affordance, and compact but readable density.
  Notes: table rows now have hover/selected states, focusable row actions, `aria-expanded`, title truncation, and compact evidence grouping.
  Acceptance: click selection opens the shared detail drawer and keyboard focus remains visible.

## 5. Detail Drawer

- [x] 5.1 Implement or refine a shared `Detalle de licitación` drawer for Explorer and Radar.
  Notes: detail should preserve table/board context rather than navigating away by default.
  Notes: shared drawer is keyed by `selectedNoticeId` for both Explorer and Radar, labels its origin context, and renders summary, timeline, buyer, products/services, offers, purchase orders, certainty, and metadata when API data exists.
  Acceptance: selecting a row/card opens consistent detail sections for summary, dates, buyer, products/services, amounts, offers, awards, purchase orders, certainty, and metadata where data exists.
- [x] 5.2 Limit MVP actions to read-only safe actions.
  Notes: allowed actions are copy code, open licitación, and view full detail if already supported.
  Notes: drawer actions are limited to copying the external code and opening the public ChileCompra licitacion URL when a code exists.
  Acceptance: no assignment, notes, discard, AI analysis, workflow mutation, or persistent drag-and-drop actions are introduced.

## 6. Radar Board

- [x] 6.1 Implement the Radar board grouped by derived stage.
  Notes: use columns for Abiertas, Cierra pronto, Cerradas, Adjudicadas, Revocadas o suspendidas, and Sin clasificar.
  Notes: Radar renders the six derived-stage columns from the shared stage contract, and each card opens the shared `Detalle de licitación` drawer.
  Acceptance: every rendered card represents one licitación/notice and opens the shared detail drawer.
- [x] 6.2 Harden card visual density and board overflow behavior.
  Notes: cards should show only scan-critical data and the board may scroll horizontally if needed.
  Notes: board uses stable horizontal columns, compact evidence chips, focus/selected states, and horizontal overflow on narrow screens; no drag/drop behavior is present.
  Acceptance: Radar remains usable on desktop and degrades predictably on mobile.

## 7. Resilience, Accessibility, and Validation

- [x] 7.1 Add loading, empty, and error states for workspace data.
  Notes: loading should use skeletons or stable placeholders; errors should be actionable.
  Notes: list, pulse, and detail states use skeletons, explicit unavailable states, actionable retry/clear actions, and `role=status`/`role=alert` announcements.
  Acceptance: API loading/failure/empty states do not collapse layout or show misleading data.
- [x] 7.2 Validate frontend quality gates and runtime behavior.
  Notes: use frontend-local checks for TypeScript/lint/build if available; use Docker-first backend runtime if API-backed smoke data is needed.
  Notes: validated with `npm.cmd run typecheck`, `npm.cmd run lint`, and `npm.cmd run build`; build required elevated execution after sandboxed `spawn EPERM`.
  Acceptance: validation results are reported with exact commands and any blockers.
- [x] 7.3 Update docs or product notes if final labels, boundaries, or validation steps differ from current documentation.
  Notes: keep docs concise and implementation-aligned.
  Notes: `client/README.md` now documents Explorer/Radar, shared read-only drawer, API-backed pulse behavior, validation commands, and MVP boundaries.
  Acceptance: docs do not describe future workflow features as implemented.

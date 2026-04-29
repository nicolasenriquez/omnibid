## 1. Frontend Baseline and Contract Audit

- [ ] 1.1 Inspect the current `client/` structure, `/licitaciones` route, opportunity API client, view models, and styling approach.
  Notes: do not overwrite untracked generated artifacts under `client/.next` or `client/node_modules`.
  Acceptance: implementation plan identifies the exact components and contracts to change before code edits.
- [ ] 1.2 Freeze the Spanish label and stage mapping contract for user-visible UI.
  Notes: internal TypeScript names may stay in English; rendered labels must be Spanish.
  Acceptance: no raw field names such as `derivedStage` or `externalNoticeCode` appear in user-visible UI.

## 2. SaaS Workspace Shell and Navigation

- [ ] 2.1 Build or refine the `/licitaciones` workspace shell with premium operational visual hierarchy.
  Notes: use restrained surfaces, borders, spacing, typography, and contrast; avoid marketing-style hero treatment.
  Acceptance: shell supports desktop-first use and does not break on narrow screens.
- [ ] 2.2 Add or refine the `Explorador` / `Radar` tab switcher.
  Notes: the active tab must have clear visual state, accessible focus, and no English UI labels.
  Acceptance: switching views preserves applicable filter and selected-opportunity context where practical.

## 3. Pulse Metrics and Filters

- [ ] 3.1 Implement `Pulso de oportunidades` from available summary/stage counts.
  Notes: chips may act as quick filters if current state management supports it.
  Acceptance: counts are API-backed or gracefully unavailable; no fake numbers are rendered.
- [ ] 3.2 Harden the filter workspace.
  Notes: primary filters should be visible; advanced filters should be progressive and not crowd the first view.
  Acceptance: active filter state is visible and `Limpiar filtros` reliably resets supported filters.

## 4. Explorer Table

- [ ] 4.1 Render the Explorer as one parent row per licitación/notice.
  Notes: parent rows must not duplicate licitaciones by line, offer, supplier, or purchase-order evidence.
  Acceptance: list grain is visibly and structurally one row per notice.
- [ ] 4.2 Add hierarchical expansion for child evidence.
  Notes: show lines/items, offers, awards, and purchase-order evidence only when supported by API data.
  Acceptance: uncertainty is shown with relationship certainty labels instead of being implied as fact.
- [ ] 4.3 Add table interaction hardening.
  Notes: include selected row state, hover state, focus state, truncation affordance, and compact but readable density.
  Acceptance: click selection opens the shared detail drawer and keyboard focus remains visible.

## 5. Detail Drawer

- [ ] 5.1 Implement or refine a shared `Detalle de licitación` drawer for Explorer and Radar.
  Notes: detail should preserve table/board context rather than navigating away by default.
  Acceptance: selecting a row/card opens consistent detail sections for summary, dates, buyer, products/services, amounts, offers, awards, purchase orders, certainty, and metadata where data exists.
- [ ] 5.2 Limit MVP actions to read-only safe actions.
  Notes: allowed actions are copy code, open licitación, and view full detail if already supported.
  Acceptance: no assignment, notes, discard, AI analysis, workflow mutation, or persistent drag-and-drop actions are introduced.

## 6. Radar Board

- [ ] 6.1 Implement the Radar board grouped by derived stage.
  Notes: use columns for Abiertas, Cierra pronto, Cerradas, Adjudicadas, Revocadas o suspendidas, and Sin clasificar.
  Acceptance: every rendered card represents one licitación/notice and opens the shared detail drawer.
- [ ] 6.2 Harden card visual density and board overflow behavior.
  Notes: cards should show only scan-critical data and the board may scroll horizontally if needed.
  Acceptance: Radar remains usable on desktop and degrades predictably on mobile.

## 7. Resilience, Accessibility, and Validation

- [ ] 7.1 Add loading, empty, and error states for workspace data.
  Notes: loading should use skeletons or stable placeholders; errors should be actionable.
  Acceptance: API loading/failure/empty states do not collapse layout or show misleading data.
- [ ] 7.2 Validate frontend quality gates and runtime behavior.
  Notes: use frontend-local checks for TypeScript/lint/build if available; use Docker-first backend runtime if API-backed smoke data is needed.
  Acceptance: validation results are reported with exact commands and any blockers.
- [ ] 7.3 Update docs or product notes if final labels, boundaries, or validation steps differ from current documentation.
  Notes: keep docs concise and implementation-aligned.
  Acceptance: docs do not describe future workflow features as implemented.

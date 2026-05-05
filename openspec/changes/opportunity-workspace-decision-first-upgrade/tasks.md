## 1. Investigation and Contract Freeze

- [ ] 1.1 Confirm current opportunity API/data coverage for decision-flow fields.
  Notes: validate list/detail contracts and DB-backed availability for status, stage, amount, dates, buyer, category, procurement type, less-than-100-UTM, lines/offers/purchase-order evidence.
  Notes: include explicit gap list for fields not currently exposed.
  Acceptance: scope references only corroborated fields; missing fields are documented as gaps.
- [ ] 1.2 Confirm Compra Agil source coverage.
  Notes: validate `normalized_ordenes_compra.es_compra_agil` and `silver_purchase_order.is_agile_purchase_flag`.
  Acceptance: dedicated Compra Agil lane requirements are tied to existing source fields.
- [ ] 1.3 Freeze MVP action semantics and read-only boundaries.
  Notes: `Descartar` local-session only; no persistent mutation APIs in this slice.
  Acceptance: CTA behavior matrix is explicit and consistent with current architecture docs.
- [ ] 1.4 Build an exact data-fit matrix from live DB evidence.
  Notes: capture the current coverage for notices, lines, bids, awards, purchase orders, annotations, procurement-mode flags, and data-quality issues; include the zero-coverage `has_site_visit_flag` case and the partial annotation coverage counts.
  Acceptance: the proposal can clearly separate supported, partial, and unavailable claims.
- [ ] 1.5 Define signal coverage semantics for the UI contract.
  Notes: supported, partial, unavailable, with explicit `Sin dato` / `Cobertura parcial` fallbacks; partials remain visibly partial, zero-coverage signals never become primary badges.
  Acceptance: sparse or zero-coverage signals cannot be surfaced as complete truths.
- [ ] 1.6 Separate benchmark guidance from implementation commitments.
  Notes: TodoLicitaciones research informs market direction and UI scanability only; only data-backed repo capabilities may enter this slice.
  Acceptance: SEO, alerts, watchlists, export, and extra procurement-mode lanes remain explicit future slices.

## 2. Sprint 1 - Decision Flow Core

- [ ] 2.1 Implement compact decision-first header and KPI strip.
  Notes: minimize landing-style hero footprint; maximize operational scannability.
  Acceptance: first viewport answers urgency and review load quickly.
- [ ] 2.2 Set `Lista` as default with preserved `Tabla` and `Radar` context.
  Notes: keep filter/query state stable on view switches.
  Acceptance: multi-view navigation remains stable and context-preserving.
- [ ] 2.3 Harden search and primary filter surface.
  Notes: search targets code, buyer, category/product text where available.
  Acceptance: controls are keyboard-accessible and state is visibly clear.
- [ ] 2.4 Reframe detail drawer as evidence package.
  Notes: include summary, why-it-matters, dates, buyer, amount, products, evidence, and human-review disclaimer.
  Acceptance: drawer supports decision review without implying legal/commercial automation.
- [ ] 2.5 Separate Data Center emphasis from commercial flow.
  Notes: move upload/log-heavy UX out of main `/licitaciones` attention zone.
  Acceptance: `/licitaciones` retains only concise trust/status indicators.

## 3. Sprint 2 - Business Decision Primitives

- [ ] 3.1 Add supplier profile input model (initial scope).
  Notes: profile includes rubros, regions, product/ONU hints, amount range, restrictions.
  Acceptance: profile exists with deterministic, auditable data model.
- [ ] 3.2 Implement deterministic compatibility signals.
  Notes: no predictive labels or persisted scores in Silver; each signal exposes rule/source.
  Acceptance: signals render `compatible`/`warning`/`incompatible`/`unknown` with provenance.
- [ ] 3.3 Add human bid/no-bid checklist block in detail drawer.
  Notes: deadlines, documents, fit, risks, and human review steps.
  Acceptance: checklist is visible and clearly marked as human-decision aid.
- [ ] 3.4 Add local-session CTA behavior (`Radar`, `Descartar`) with explicit copy.
  Notes: action feedback must state local/session scope when not persisted.
  Acceptance: users are not misled into assuming persistent workflow changes.

## 4. Sprint 3 - Source Intelligence

- [ ] 4.1 Implement Compra Agil dedicated lane.
  Notes: use corroborated agile flags and source-specific filters.
  Acceptance: Compra Agil view is functionally distinct from tender list flow.
- [ ] 4.2 Add buyer intelligence snapshot.
  Notes: compute deterministic historical aggregates only from available Silver facts.
  Acceptance: insufficient-data cases render explicit fallback copy.
- [ ] 4.3 Add historical comparables and closing-soon alert cues.
  Notes: deterministic only, no predictive confidence claims.
  Acceptance: comparables/alerts improve triage without fabricated certainty.

## 5. Sprint 4 - Guarded AI/NLP Extension (Future)

- [ ] 5.1 Define prerequisites for bases/document intelligence.
  Notes: do not claim requirement extraction unless document pipeline is implemented.
  Acceptance: dependency checklist exists before any AI extraction work.
- [ ] 5.2 Define semantic search extension path.
  Notes: start with deterministic synonym dictionary / category expansions; keep explainability.
  Acceptance: semantic features are staged and source-traceable.

## 6. Validation, Docs, and Delivery

- [ ] 6.1 Run frontend quality gates.
  Notes: typecheck, lint, build, and route-level smoke on `/licitaciones`.
  Acceptance: command outputs and blockers are recorded.
- [ ] 6.2 Run accessibility and responsive verification.
  Notes: keyboard flow, focus, contrast, reduced motion, touch target checks.
  Acceptance: critical issues fixed or documented before merge.
- [ ] 6.3 Update documentation and changelog.
  Notes: update product/architecture/workspace docs and `CHANGELOG.md`; keep proposal, design, and spec aligned on the same current-slice boundary.
  Acceptance: docs reflect decision-system scope, read-only guardrails, and explicit future-slice boundaries exactly.
- [ ] 6.4 Document deferred-opportunity boundaries.
  Notes: capture watchlists, alerts, public SEO, evidence export, trust signals, semantic facets, extra procurement-mode lanes, and line-level handoff as future work only.
  Acceptance: proposal, design, and spec all mark these as valuable but out of scope for this slice.

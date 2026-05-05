## Why

The current `/licitaciones` workspace already delivers read-only Explorador and Radar workflows, manual CSV ingestion entry points, and a premium polish baseline. Still, operators must parse too much UI surface before answering the core question: which opportunities deserve review today and why.

This slice is the human-facing consumer of the same decision program driven by the foundation and Gold ML changes. It should read Silver facts today and, once available, consume Gold ranking/evidence outputs without redefining the upstream contract.

The benchmark behavior from TodoLicitaciones is strong on fast scanability (title, status, type, buyer, region, dates, amount, required products), but Omnibid must go further than a public listing. Omnibid must feel like a premium supplier-side decision workspace: detect, prioritize, explain fit and gaps, package evidence, and support human bid/no-bid decisions without implying automated legal or commercial authority.

A live DB verification pass (2026-05-03) confirms the repo already has high-coverage deterministic data to support this direction:
- `silver_notice`: `122400` rows
- `silver_notice_line`: `565146` rows
- `silver_bid_submission`: `2111924` rows
- `silver_award_outcome`: `2111464` rows
- `silver_purchase_order`: `2394889` rows
- `silver_purchase_order_line`: `6668038` rows
- Compra Ágil flags available:
  - `normalized_ordenes_compra.es_compra_agil = true`: `982032`
  - `silver_purchase_order.is_agile_purchase_flag = true`: `982032`

Additional coverage evidence matters because the UI must surface supported, partial, and unavailable states honestly:
- `silver_notice_purchase_order_link`: `361199` rows
- `silver_supplier_participation`: `540306` rows
- `silver_buying_org`: `1190` rows
- `silver_contracting_unit`: `5933` rows
- `silver_supplier`: `94720` rows
- `silver_category_ref`: `12435` rows
- `silver_notice_text_ann` labeled: `59737 / 122400`
- `silver_notice_line_text_ann` labeled: `60142 / 565146`
- `silver_purchase_order_line_text_ann` labeled: `683680 / 6668038`
- `hidden_budget_flag = true`: `61884`
- `multiple_stages_flag = true`: `5072`
- `requires_toma_razon_flag = true`: `1989`
- `physical_document_delivery_flag = true`: `3912`
- `extension_flag = true`: `9942`
- `notice_has_purchase_order_flag = true`: `87706`
- `notice_awarded_to_order_conversion_flag = true`: `87706`
- `has_site_visit_flag = true`: `0`
- `data_quality_issues`: `2`

## Exact Data Fit

The proposal is only air-tight if it distinguishes between what the DB already supports, what it supports only partially, and what still needs a separate slice. The current corpus is strong enough to build a serious decision workspace, but not strong enough to justify every adjacent product idea as part of this one change.

| Concern | Exact current evidence | Safe claim now | Correction to keep the proposal honest |
|---|---|---|---|
| Scan-first decision list | `122400` notices, `565146` lines, titles/descriptions/statuses/dates mostly complete, `122205` amounts, `122395` bidders/complaints | `Lista` can prioritize review using real facts, not placeholders | do not invent missing fields, use explicit unavailable states |
| Evidence drawer | line, bid, award, PO, and PO-line tables exist with lineage and counts at scale | the drawer can package evidence for human review | the drawer must not imply legal/commercial authority |
| Buyer history snapshot | notice-level enrichments plus `87706` notice->PO conversions and millions of PO/award rows | deterministic volume, competition, and materialization snapshots are feasible | keep it as a snapshot, not a predictive score |
| Semantic facets and risk badges | `59737` labeled notice text annotations, `60142` labeled line annotations, `683680` labeled PO-line annotations, plus flags like hidden budget, multiple stages, complaints, and Toma Razón | explainable highlight chips and risk cues are justified | `has_site_visit_flag` is currently `0`, so site visit must not become a core badge or filter yet |
| Procurement modes | `982032` Compra Ágil OCs, `511829` Trato Directo OCs, `247248` Convenio Marco-linked OCs | Compra Ágil is safe to introduce as the first dedicated lane | Trato Directo and Convenio Marco stay as future slices |
| Public discovery and SEO | corpus breadth across notices, buyers, suppliers, categories, and lines is large enough to publish useful pages | public route planning and content strategy are feasible | SEO is not a single feature, and no public site, sitemap, or indexing contract exists yet |
| Alerts, watchlists, export | current watchlist is client-side only, and there is no notification/export subsystem in the repo | the market pattern is real and worth following | this is future work until persistence and delivery contracts exist |
| Data trust | only `2` `data_quality_issues` are currently recorded, both on normalized category identity | a trust indicator is possible | a trust cockpit still needs its own product contract and presentation rules |

Correction rules for the whole proposal:
- benchmark research is market guidance, not implementation proof
- exact data coverage wins over attractive but unverified ideas
- partial coverage must render as `Sin dato`, `Cobertura parcial`, or equivalent explicit fallback
- if a feature needs public routing, persistence, notification delivery, or export mechanics, it is not in this slice even if the data exists
- if a signal is zero-coverage or sparse, it stays auxiliary until proven otherwise
- if a signal is partial, it must remain visibly partial even when it is useful for triage
- if a signal has zero coverage, it must never be promoted into a primary badge, ranking input, or recommendation

## What Changes

- Reframe `/licitaciones` into a supplier-side decision-first information architecture:
  - executive header with business KPIs that answer urgency and review load.
  - large search entry point for code, buyer, product/category, and description terms.
  - business-priority filters in a clear primary/advanced split.
  - default `Lista` view optimized for fast scan.
  - secondary `Tabla` and `Radar` views for dense analysis and stage operations.
- Normalize user-visible labels to Spanish procurement language with proper accents, and keep raw backend field names out of UI copy.
- Separate technical ingestion concerns from commercial review flow:
  - keep concise data freshness/status indicators inside `/licitaciones`.
  - move CSV upload timeline/log console emphasis into a dedicated `Centro de Ingesta` surface.
- Add a premium `Opportunity List` item layout that is readable in seconds and shows:
  - título
  - código
  - estado oficial
  - tipo de licitación
  - organismo comprador
  - región
  - fecha de publicación
  - fecha de cierre
  - días restantes
  - monto estimado
  - productos requeridos
  - breve descripción
- Standardize per-opportunity actions:
  - primary: `Analizar oportunidad`
  - secondary: `Agregar al radar`, `Ver fuente`, `Descartar`
- Strengthen detail drawer as evidence package:
  - executive summary
  - why this opportunity matters now
  - key dates
  - buyer and amount
  - required products/services
  - opportunity and risk signals with explicit `supported` / `partial` / `unavailable` coverage states
  - buyer history snapshot (when data exists)
  - source evidence
  - human checklist for bid/no-bid review
  - recommended next actions
  - explicit human-review reminder before bid decisions
- Add supplier-profile-driven compatibility signals with deterministic, explainable rules:
  - supplier profile inputs (rubros, regiones, productos/codigos ONU, amount range, restrictions).
  - explainable signals only from available fields, never from inferred completeness.
  - no predictive scores persisted in Silver.
- Add a dedicated Compra Ágil opportunity source lane when data is available:
  - separate view semantics from large tender exploration.
  - source-specific filters and urgency model.
  - use only validated agile-flagged records from the current corpus; do not infer Compra Ágil from unrelated fields.
  - other procurement modes remain future slices, even though the DB already contains partial support for them.
- Keep scope aligned to current MVP constraints:
  - no AI legal/commercial authority
  - no assignment/notes/workflow mutation persistence in this slice
  - no fabricated metrics when data is unavailable

## Capabilities

### New Capabilities

- `opportunity-workspace-decision-flow`: Decision-first supplier-side workspace flow with scan-first list design, evidence drawer, and human-review guardrails.
- `supplier-profile-compatibility-signals`: Supplier profile inputs and deterministic compatibility signals with explicit rule provenance; no predictive persistence in Silver.
- `opportunity-evidence-package`: Shared evidence model for opportunity detail, including source fields, missing-data states, key dates, buyer context, products, requirements proxy signals, and checklist.
- `compra-agil-opportunity-source`: Dedicated Compra Ágil surface using available agile indicators from purchase-order-backed data and source-specific filter behavior.
- `buyer-intelligence-snapshot`: Deterministic historical buyer context (volume, typical amount bands, competition and materialization indicators) when enough data exists.

### Modified Capabilities

- `opportunity-workspace-premium-frontend`: Extend read-only workspace composition to include `Lista` as default view and stronger decision-oriented navigation hierarchy.
- `opportunity-workspace-premium-polish`: Extend visual polish contract from component-level refinement to full decision-flow hierarchy, CTA semantics, and cognitive-load reduction.

## Impact

- Affected frontend areas:
  - `client/app/licitaciones/`
  - `client/src/features/opportunity-workspace/`
  - `client/src/lib/api/`
  - `client/src/lib/url-state/`
  - `client/src/types/`
  - `client/src/styles/`
- Backend read-contract impact:
  - `backend/api/routers/opportunities.py`
  - `backend/api/opportunities_contract.py`
  - `backend/api/opportunities_query.py`
  - possible new read-only routers for buyer snapshot and Compra Ágil lane if current contracts cannot support required fields
  - no new write endpoints
- Affected contracts:
  - `/opportunities` list/detail DTO-to-view-model mapping for scan fields and evidence labels
  - new deterministic compatibility-signal contract (supplier profile input + explainable output)
  - read-only action boundaries remain explicit (`Descartar` local-session only in MVP)
- Documentation impact:
  - update workspace and product docs to reflect decision-flow model, `Lista` default, action semantics, `Centro de Ingesta` separation, and human-review language
  - update `CHANGELOG.md` when implemented
- Operational impact:
  - frontend validation remains local-first for UI gates, with Docker-backed backend data for integration smoke
  - DB-backed evidence checks are required before exposing new business filters/signals in UI

## Adjacent Opportunities Not Yet in This Slice

The research, the current repo surface, and the domain docs show several high-value follow-ups that are intentionally out of scope for this upgrade. They belong in the proposal because they are real product opportunities, but they must remain separate from the current decision-first slice.

| Opportunity | Evidence already present in repo/docs/DB | Why it matters | Why it stays deferred |
|---|---|---|---|
| Persistent watchlists and saved searches | UI analysis docs show a client-side watchlist in `localStorage`; the current workspace already supports star/filter behavior | Retention and repeat review workflows become durable across sessions and devices | This slice stays read-only and does not introduce persisted user state |
| Deadline-driven alerts and calendarization | Domain docs model forum, answer publication, technical opening, economic opening, adjudication, and PO milestones; Silver already has `days_remaining` and date chains | Turns review cues into proactive operator workflows instead of passive scan-only cues | This slice adds urgency cues only, not notification delivery or calendars |
| Public discovery and SEO | Current product docs frame `/licitaciones` as a private workspace, not a public acquisition surface | Indexable landing pages can create top-of-funnel demand and surface long-tail opportunities | This requires a separate public surface, routing, and indexing strategy |
| Evidence packaging and sharing | Product vision already calls for bounded context export for downstream review; the detail drawer is evidence-first | Makes internal review, handoff, and offline discussion much easier | This slice packages evidence visually, but does not add share/export mechanics |
| Trust and data-quality signals | `data_quality_issues`, persisted summary snapshots, and the current operational metrics layer already exist | Users can judge whether the workspace is sufficiently fresh and trustworthy before acting | A dedicated trust cockpit needs its own presentation and operational rules |
| Semantic facets and risk badges | Silver annotations are populated, and the repo already has deterministic flags like hidden budget, multiple stages, complaints, and Toma Razón | These are high-signal triage helpers with explainable provenance | This slice uses a few existing signals, but not a full facet system or badge taxonomy |
| Procurement-mode expansion | Domain docs distinguish licitación pública, Compra Ágil, Convenio Marco, and Trato Directo | Broader coverage gives a more complete procurement workspace | The current change keeps Compra Ágil as the first extra lane and defers the rest |
| Line-level investigation handoff | Architecture and data model docs already define planned procurement-line investigation read models | Hard cases need a deeper analyst handoff than a notice-level view | This is a separate workspace slice with its own bounded context |

These items are strong follow-ups because the repo already has the enabling data or the domain scaffolding. They stay out of this slice so the current change remains a focused decision-first workspace upgrade instead of turning into a broader procurement platform program.

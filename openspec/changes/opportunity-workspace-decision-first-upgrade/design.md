## Context

Omnibid already has a read-only Opportunity Workspace with Explorador/Radar, upload flow, and premium polish baseline. The next step is not cosmetic. It is business-flow clarity:

- find opportunities fast
- explain why they matter
- detect fit/gap signals
- package evidence for human review
- support bid/no-bid decision workflow without claiming autonomous authority

Benchmark inspiration from TodoLicitaciones is functional (scanability), not visual copying. Omnibid remains a premium supplier-side decision workspace.

This change stays inside current repo boundaries:
- read-only opportunity investigation MVP
- no predictive score persistence in Silver (`*_score`, `*_probability`, `future_*`)
- human review remains mandatory for legal/commercial decisions

## Terminology Boundary

- User-visible labels use Spanish procurement language and proper accents: `Licitación`, `Lista`, `Tabla`, `Radar`, `Pública`, `Región`, `Publicación`, `Código`, `Compra Ágil`.
- Raw backend field names such as `noticeId`, `externalNoticeCode`, and `derivedStage` stay out of visible labels.
- Internal implementation names can remain technical, but the rendered UI copy must read like business language, not schema language.

## Verified Data Surface (Corroborated)

Read contracts and live DB checks (2026-05-03) confirm these fields/data already exist:

- Opportunity list/detail contracts already expose:
  - notice code/title/status/stage
  - amount/currency/publication/close/days remaining
  - buyer name/region
  - category/procurement type/less-than-100-UTM flag
  - lines/offers/purchase-order evidence + relationship certainty
- Silver/Normalized tables hold high-volume facts for history signals:
  - `silver_notice`, `silver_notice_line`, `silver_bid_submission`, `silver_award_outcome`, `silver_purchase_order`, `silver_purchase_order_line`
- Compra Ágil indicators are present in order-backed datasets:
  - `normalized_ordenes_compra.es_compra_agil`
  - `silver_purchase_order.is_agile_purchase_flag`

Implication:
- We can implement deterministic decision helpers now without inventing data.
- We must not promise requirement/document extraction or legal-read automation as already available facts.

## Goals / Non-Goals

**Goals**
- Make `/licitaciones` answer “what should I review today and why?” in first viewport.
- Keep scanability first with `Lista` default.
- Preserve `Tabla` and `Radar` as dense analysis surfaces.
- Add supplier-profile compatibility signals with explainable rules.
- Add human checklist and evidence package structure in detail drawer.
- Separate technical ingestion UI from commercial review flow.
- Add dedicated Compra Ágil lane using existing agile indicators.

**Non-Goals**
- Rebuild ingestion/pipeline architecture.
- Persist predictive scores or autonomous recommendations in Silver.
- Claim unavailable structured fields as existing (e.g., legal doc compliance truth).
- Add persistent workflow mutation (assignment/notes/discard persistence) in this slice.

## Decisions

1. **Decision-flow over listing-flow.**
   - `/licitaciones` is treated as commercial review queue, not just tender table.

2. **Default `Lista`, keep `Tabla` + `Radar`.**
   - `Lista` optimizes quick triage; dense views remain for deeper inspection.

3. **`Centro de Ingesta` separation.**
   - Upload console/log-heavy interactions move out of main decision surface.

4. **Supplier profile is deterministic and explainable.**
   - Profile inputs are user-provided and evaluated with explicit rules over existing data fields.
   - No predictive score semantics and no Silver persistence of “AI fit”.

5. **`Descartar` is local-session only in MVP.**
   - Avoids false expectation of persistent workflow mutation until write APIs exist.

6. **Compra Ágil is source-specific lane.**
   - Backed by existing agile flags in order datasets; not inferred from unrelated fields.

7. **Future tabs stay absent unless implemented.**
   - No disabled placeholder tabs for `Mapa/Regiones` or `Historico` in this slice.

8. **Business labels stay in Spanish procurement language.**
   - Use accents and domain terms in all visible copy.
   - Keep raw backend field names out of labels and control text.

## UX Architecture

### Layer A: Decision Header
- compact operational header
- KPI strip: abiertas, cierran pronto, alto monto, en radar, sin revisar
- data trust indicators: source freshness, coverage window, API health

### Layer B: Exploration
- strong search input (code, buyer, product/category, description)
- primary filters first, advanced filters progressive
- view switch: `Lista` (default), `Tabla`, `Radar`, `Compra Ágil` (when available)

### Layer C: Evidence and Actions
- shared detail drawer as “evidence package”
- per-opportunity CTA stack:
  - primary `Analizar oportunidad`
  - secondary `Agregar al radar`, `Ver fuente`, `Descartar` (local session)
- fixed human-review disclaimer

### Layer D: Data Operations
- `Centro de Ingesta` route/surface for CSV flows, ingestion logs, diagnostics
- `/licitaciones` keeps only minimal trust/status indicators

## Deterministic Compatibility Signals (No Prediction Claims)

Inputs (profile):
- rubros/categories
- regions
- products/ONU codes
- amount range
- restrictions/exclusions
- optional readiness flags

Rule outputs (examples):
- `Producto compatible` from category/ONU/text overlap
- `Región compatible` from buyer region vs profile region
- `Monto en rango` from estimated amount
- `Cierre dentro de ventana` from close date
- `Falta dato clave` when required source field is null

All signals must expose:
- source field(s)
- rule applied
- result state (`compatible`, `warning`, `incompatible`, `unknown`)

## Buyer Intelligence Snapshot (Deterministic)

Potential metrics from existing Silver facts:
- comparable notices count (time-bounded)
- typical awarded/estimated amount band
- average bid/supplier competition
- notice-to-purchase-order materialization indicators
- recurring supplier presence

Display policy:
- render only when enough data
- otherwise show `Sin historial suficiente en la base cargada`

## Compra Ágil Lane (Data-Backed)

Source strategy:
- derive from order-backed agile flags (`is_agile_purchase_flag` / `es_compra_agil`)
- keep separated from main tender list semantics

Initial filter intent:
- recency / closing urgency
- buyer/service
- region
- keyword/product/category
- amount ceiling and eligibility reminders as informational copy (not legal determination)

## Risk / Trade-offs

- **[Risk] Scope overlaps active polish/upload work.**
  - Mitigation: this change targets decision IA/business primitives; upload internals remain unchanged.

- **[Risk] Some desired signals need new read endpoints/aggregates.**
  - Mitigation: ship strict progressive enhancement; unknown fields render typed unavailable states.

- **[Risk] Compatibility signals misread as recommendations.**
  - Mitigation: enforce neutral “signals/checklist” language and explicit human decision disclaimer.

- **[Risk] Compra Ágil semantics drift from source reality.**
  - Mitigation: bind lane rules only to validated agile flags and documented source constraints.

## Migration Plan

### Sprint 1: Decision Flow Core
1. Compact header and KPI strip.
2. `Lista` default scan-first view.
3. Search + primary filters.
4. Evidence-first drawer reordering.
5. Move upload console emphasis to `Centro de Ingesta`.

### Sprint 2: Business Decision Primitives
1. Supplier profile (initial UI/input model).
2. Deterministic compatibility signals.
3. Human bid/no-bid checklist.
4. Local-session CTA semantics.
5. Review package export/copy helpers.

### Sprint 3: Source Intelligence
1. Compra Ágil dedicated lane.
2. Buyer history snapshot.
3. Historical comparables.
4. Closing-soon operational alerts.

### Sprint 4: AI/NLP Extension (Future Guarded)
1. Bases summarization/extraction only when source/document pipeline exists.
2. Semantic search enhancements.
3. Explainable ranking assists with mandatory human review.

Rollback strategy:
- keep changes isolated to `client/` and read-only backend contracts
- gate new lanes/features behind explicit view toggles
- fallback to current Explorador/Radar surfaces if regression appears

## Open Questions

None.

## Why

The current `/licitaciones` workspace already delivers read-only Explorador and Radar workflows, manual CSV ingestion entry points, and a premium polish baseline. Still, operators must parse too much UI surface before answering the core question: which opportunities deserve review today and why.

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
  - opportunity and risk signals
  - buyer history snapshot (when data exists)
  - source evidence
  - human checklist for bid/no-bid review
  - recommended next actions
  - explicit human-review reminder before bid decisions
- Add supplier-profile-driven compatibility signals with deterministic, explainable rules:
  - supplier profile inputs (rubros, regiones, productos/codigos ONU, amount range, restrictions).
  - explainable signals only from available fields.
  - no predictive scores persisted in Silver.
- Add a dedicated Compra Ágil opportunity source lane when data is available:
  - separate view semantics from large tender exploration.
  - source-specific filters and urgency model.
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

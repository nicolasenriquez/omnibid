# Omnibid — Project Description for UI/UX Video Analysis Agent

## Purpose

This document provides a complete project description for an AI agent that will analyze a video capture (MP4 or screenshot sequence) of the Omnibid `/licitaciones` (Opportunity Workspace) user interface. The goal is to enable the agent to understand what it sees on screen, identify UI components, map visual elements to application concepts, and provide detailed UI/UX feedback.

---

## 1. Project Overview

**Product**: Omnibid (also called "App ChileCompra")
**Tagline**: Supplier-side decision workspace for Chilean public procurement (Mercado Público / ChileCompra)
**Purpose**: Help suppliers detect, prioritize, and investigate public tender opportunities ("licitaciones") and purchase orders ("órdenes de compra") from Chile's Mercado Público platform, packaged as a deterministic data platform with a premium review UI.

**Core Value Proposition**: Instead of browsing a raw listing, suppliers get a decision-first workspace that answers "what should I review today and why?" — with evidence packages, compatibility signals, and bid/no-bid checklists.

**Domain**: Chilean public procurement (Spanish-language; all user-facing labels are in Spanish with proper accents: `Licitación`, `Región`, `Publicación`, `Adjudicada`, `Compra Ágil`).

---

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TypeScript 5.8 |
| Styling | Tailwind CSS 4 + custom CSS design tokens (`tokens.css` + `workspace.css`) |
| Backend | FastAPI (Python 3.12+) |
| ORM | SQLAlchemy 2.x (declarative models) |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Runtime | Docker Compose (`docker-compose.yml` + `.env.docker`) |
| Task Runner | `just` (justfile recipes) |
| Package Manager | `uv` |
| Locale | `es-CL` (Chilean Spanish; all formatting uses `Intl.NumberFormat` / `Intl.DateTimeFormat` with `es-CL`) |

---

## 3. Architecture Overview

```
client/ (Next.js 16 + React 19 frontend)
  app/licitaciones/page.tsx          → Route entry point
  src/features/opportunity-workspace/ → Main feature module
  src/lib/api/                       → HTTP client + API functions
  src/lib/url-state/                 → URL query state sync
  src/lib/formatters/                 → Display formatting helpers
  src/types/                         → TypeScript type definitions
  src/components/ui/                  → Shared UI primitives
  src/styles/tokens.css              → Design tokens
  src/styles/workspace.css            → Workspace-specific styles

backend/ (FastAPI)
  api/routers/opportunities.py        → REST endpoints
  api/opportunities_contract.py       → Pydantic response models
  api/opportunities_query.py          → SQL query builders
  models/                             → SQLAlchemy ORM models
    raw.py        → Raw ingestion tables
    normalized.py → Normalized + Silver tables
    operational.py → SourceFile, PipelineRun, IngestionBatch, DataQualityIssue
  db/                                → Engine, session, Base
  core/                              → Config, errors, app wiring

openspec/changes/                    → Change management system
```

### Data Flow

```
CSV Files → Raw Layer (append-only) → Normalized Layer (dedup/upsert) → Silver Layer (cross-referenced, enriched) → Gold (deferred)
```

Each layer preserves `source_file_id`, `ingestion_batch_id`, and `row_hash_sha256` for full traceability.

---

## 4. Frontend Entry Point & Routing

The main user-facing page is `/licitaciones`, which renders the `<OpportunityWorkspace />` component.

**File**: `client/app/licitaciones/page.tsx`
**Component**: `client/src/features/opportunity-workspace/workspace.tsx`

The workspace is a single-page application with state synchronized to URL search params (no page reloads for filtering/pagination/sorting).

---

## 5. Current UI Layout (Implemented — v0.1.0)

### 5.1 Workspace Header

A dark gradient banner (`workspace-header`) containing:
- **Kicker badge**: "Licitaciones" label in a pill badge
- **Title**: "Oportunidades" in large white text (2.2rem, bold)
- **Subtitle**: Description text
- **KPI metrics strip**: Shows key counts using `.pulse-chip` elements:
  - `Abiertas` (open) — green chip
  - `Cierran pronto` (closing_soon) — amber chip
  - `Adjudicadas` (awarded) — deep blue chip
  - `Monto total` (total_estimated_amount) — formatted as CLP currency
  - Additional metrics from API: `closed`, `revoked_or_suspended`, `total_opportunities`
- **Data freshness indicator**: Shows last data update timestamp
- **Upload trigger button**: Opens the manual CSV upload sheet

### 5.2 Filter Panel

Located below the header (`filter-panel`, `filter-grid`):
- **Search input** (`input-with-icon`): Free-text search across title, code, buyer, category
- **Primary filter row** (5-column grid):
  - `Estado oficial` (official status dropdown)
  - `Etapa` (stage dropdown: Abierta, Cierra pronto, Cerrada, Adjudicada, Revocada o suspendida)
  - `Región comprador` (buyer region dropdown)
  - `Categoría` (primary category dropdown)
  - `Fecha cierre` (date range: close from/to)
- **Advanced filters** (collapsible `<details>` element):
  - `Fecha publicación` (publication date range)
  - `Monto mínimo` / `Monto máximo` (amount range)
  - `Tipo licitación` (procurement type: Pública, Privada, Servicios)
  - `Menor a 100 UTM` (checkbox: less than 100 UTM flag)
- **Active filter chips** (`active-filter-row`): Shows applied filter labels with remove buttons
- **Filter action buttons**:
  - `Refrescar` (Refresh) — reloads data
  - `Limpiar filtros` (Clear filters) — resets to defaults

### 5.3 Toolbar

Sticky toolbar (`workspace-toolbar`) below filters:
- **View tabs** (pill-style `ui-tabs`):
  - `Lista` (Explorer) — table/list view (default)
  - `Radar` — Kanban-style board by stage
- **Result count**: "X oportunidades" with total/filtered counts
- **Sort controls**: Sortable by `close_date`, `publication_date`, `estimated_amount`, `days_remaining`
- **Watchlist filter toggle**: Button to filter to watchlisted opportunities only
- **Pagination**: Page navigation with `Anterior` / `Siguiente`

### 5.4 Explorer (Table) View — `WorkspaceExplorerTable`

A responsive data table (`ui-table-wrap` + `ui-table`) with columns:
- ★ (watchlist star toggle)
- `Código` (external notice code)
- `Título` (notice title, truncated)
- `Estado` (official status)
- `Etapa` (derived stage, color-coded `status-chip`)
- `Comprador` (buyer name)
- `Región` (buyer region)
- `Publicado` (publication date)
- `Cierre` (close date)
- `Días` (days remaining)
- `Monto` (estimated amount, formatted CLP)

Each row is clickable to open the detail pane. Selected row gets `.ui-table-row-active` highlight.

**Expanded row panel** (`table-evidence-panel`): When a row is expanded, shows a mini evidence card with:
- Title and external code
- Stage badge
- Summary facts (amount, dates, buyer, category)
- Evidence groups (lines, offers, purchase orders)
- Actions: "Copiar código", "Abrir licitación"

### 5.5 Radar (Board) View — `WorkspaceRadarBoard`

Six-column Kanban board (`radar-board`) with stage columns:
1. `Abierta` (open) — green accent
2. `Cierra pronto` (closing_soon) — amber accent
3. `Cerrada` (closed) — gray accent
4. `Adjudicada` (awarded) — deep blue accent
5. `Revocada o suspendida` (revoked_or_suspended) — red accent
6. `Sin clasificar` (unknown) — red/gray accent

Each card (`opportunity-card`) shows:
- External notice code (accent color, small)
- Title (bold, truncated)
- Amount, dates, buyer, category, days remaining
- Evidence chips: line count, offer count, purchase order count with relationship certainty badges

### 5.6 Detail Pane — `WorkspaceDetailPane`

A sticky side panel (`workspace-detail`) that slides in from the right (min 340px, max 440px) when an opportunity is selected:

**Header section** (`workspace-detail__header`):
- Close button (×)
- External notice code
- Official status badge
- Derived stage badge (color-coded)

**Action bar** (`workspace-detail__actions`):
- `Copiar código` — copy external notice code to clipboard
- `Abrir licitación` — open ChileCompra external URL
- `Analizar oportunidad` — primary CTA (currently opens detail)

**Content sections** (`detail-section`):
1. **Summary** — title, amount, dates, buyer, category, procurement type
2. **Timeline** — publication, close, award dates with source markers
3. **Buyer** — name, region, contracting unit
4. **Lines** (`OpportunityLineEvidence`) — item code, product code, name, description, quantity, unit, offer count, supplier count, relationship certainty
5. **Offers** (`OpportunityOfferEvidence`) — with view mode toggle (summary vs all):
   - Supplier, offer name, status, amount, unit price, quantity, currency
   - Selected offer badge (winner indicator)
6. **Purchase Orders** (`OpportunityPurchaseOrderEvidence`) — PO code, status, date, amount, relationship certainty

**Relationship certainty labels**:
- `Alta` (high) — strong match
- `Media` (medium) — moderate match
- `Baja` (low) — weak match
- `Sin evidencia` (none) — no evidence
- `No confirmada` (unconfirmed) — not yet confirmed

### 5.7 Watchlist

Client-side watchlist stored in `localStorage` under key `opportunity-workspace.watchlist.v1`. Users can star/unstar opportunities. The toolbar includes a filter toggle to show only watchlisted items.

### 5.8 Upload Sheet

A full-screen overlay (`upload-sheet-shell` + `upload-sheet`) that slides in from the right:
- **Dataset toggle**: Choose between `Licitaciones` and `Órdenes de compra`
- **CSV dropzone**: Drag-and-drop or click-to-upload
- **Three-step workflow** (`upload-workflow`):
  1. `Preparar` (Prepare) — select dataset type and file
  2. `Validar` (Validate) — pre-flight check (column validation, hash, size, row count)
  3. `Cargar` (Process) — trigger backend ingestion with progress tracking
- **Live console** (`upload-console`): Terminal-style log with animated status pips showing real-time progress

### 5.5 Empty/Loading/Error States

- **Loading**: Skeleton placeholders (`Skeleton` components, `.loading-stack`)
- **Empty**: `NoDataState` blocks with title, description, and optional retry action
- **Error**: `.state-block--error` with red accent, HTTP status code badge, and actionable retry button
- **No results**: "No se encontraron oportunidades. Intenta con otros filtros o más tarde."

---

## 6. Data Model & API Surface

### 6.1 API Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/opportunities/summary` | Summary metrics (counts by stage, total amount) |
| GET | `/opportunities/` | Paginated list with filters, sorting |
| GET | `/opportunities/{notice_id}` | Full detail (lines, offers, purchase orders, timeline) |
| POST | `/manual-uploads/preflight` | CSV file pre-flight validation |
| POST | `/manual-uploads/process` | Start CSV ingestion job |
| GET | `/manual-uploads/jobs/{job_id}` | Poll ingestion job status |

### 6.2 Query Parameters (List Endpoint)

| Param | Type | Description |
|---|---|---|
| `q` | string (contains) | Search across title, code, buyer, category |
| `official_status` | string (contains) | Official status filter |
| `stage` | enum | `open`, `closing_soon`, `closed`, `awarded`, `revoked_or_suspended`, `unknown` |
| `buyer_region` | string (contains) | Buyer region |
| `primary_category` | string (contains) | Product/service category |
| `publication_from` / `publication_to` | date | Publication date range |
| `close_from` / `close_to` | date | Close date range |
| `min_amount` / `max_amount` | numeric | Estimated amount range |
| `procurement_type` | enum | `public`, `private`, `service` |
| `less_than_100_utm` | boolean | Filter for <100 UTM flag |
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Items per page (default: 20) |
| `sort_by` | enum | `close_date`, `publication_date`, `estimated_amount`, `days_remaining` |
| `sort_order` | enum | `asc`, `desc` (default: `asc`) |

### 6.3 Stage Classification Logic

Stages are derived in the backend SQL query:
- **open**: `close_date > now() + 7 days`
- **closing_soon**: `close_date > now() AND close_date <= now() + 7 days`
- **closed**: `close_date <= now()` AND status is not "adjudicada", "revocada", or "suspendida"
- **awarded**: status contains "adjudicada"
- **revoked_or_suspended**: status contains "revocada" or "suspendida"
- **unknown**: `close_date IS NULL`

### 6.4 Key TypeScript Types

```typescript
type OpportunityStage = "open" | "closing_soon" | "closed" | "awarded" | "revoked_or_suspended" | "unknown";
type RelationshipCertainty = "high" | "medium" | "low" | "none" | "unconfirmed";
type WorkspaceTab = "explorer" | "radar";

interface OpportunityListItem {
  noticeId: string;
  externalNoticeCode: string | null;
  title: string | null;
  officialStatus: string | null;
  derivedStage: OpportunityStage;
  estimatedAmount: number | null;
  currencyCode: string | null;
  publicationDate: string | null;
  closeDate: string | null;
  lineCount: number | null;
  bidCount: number | null;
  supplierCount: number | null;
  purchaseOrderCount: number | null;
  buyerName: string | null;
  buyerRegion: string | null;
  primaryCategory: string | null;
  procurementType: string | null;
  isLessThan100Utm: boolean | null;
  daysRemaining: number | null;
}

interface OpportunityDetail {
  noticeId: string;
  externalNoticeCode: string | null;
  title: string | null;
  officialStatus: string | null;
  derivedStage: OpportunityStage;
  estimatedAmount: number | null;
  currencyCode: string | null;
  buyer: OpportunityBuyerSnapshot;
  relationshipSummary: RelationshipCertainty;
  timeline: OpportunityTimelineEvent[];
  lines: OpportunityLineEvidence[];
  offers: OpportunityOfferEvidence[];
  purchaseOrders: OpportunityPurchaseOrderEvidence[];
}
```

### 6.5 Backend Data Tables (Key Objects)

**Raw Layer** (append-only):
- `raw_licitaciones` — raw CSV rows from ChileCompra licitación datasets
- `raw_ordenes_compra` — raw CSV rows from purchase order datasets

**Normalized Layer** (dedup/upsert):
- `normalized_licitaciones` — cleaned, typed licitación records (122K+ rows)
- `normalized_licitacion_items` — line items per licitación (565K+ rows)
- `normalized_ofertas` — bid submissions per licitación/item (2.1M+ rows)
- `normalized_buyers` — buyer entities
- `normalized_suppliers` — supplier entities
- `normalized_categories` — product/service category taxonomy
- `normalized_ordenes_compra` — purchase orders (980K+ rows)
- `normalized_ordenes_compra_items` — PO line items

**Silver Layer** (enriched, cross-referenced):
- `silver_notice` — enriched opportunity records with derived flags
- `silver_notice_line` — enriched line items with bid statistics
- `silver_bid_submission` — structured bid data
- `silver_award_outcome` — award results
- `silver_purchase_order` — enriched purchase orders (2.4M+ rows)
- `silver_purchase_order_line` — PO line items (6.7M+ rows)
- `silver_buying_org` — buying organizations
- `silver_contracting_unit` — contracting units
- `silver_supplier` — deduplicated supplier master
- `silver_category_ref` — category reference data
- `silver_notice_purchase_order_link` — notice-to-PO relationships with confidence scores
- `silver_supplier_participation` — supplier participation facts

**Operational Layer**:
- `source_files` — file registration and tracking
- `pipeline_runs` — pipeline execution tracking
- `pipeline_run_steps` — step-level execution metrics
- `ingestion_batches` — batch ingestion tracking
- `data_quality_issues` — quality gate logs
- `dataset_summary_snapshots` — summary statistics snapshots

---

## 7. URL State Management

The workspace uses URL search params to persist all query state. This means:
- Filters, pagination, sort, selected notice, and active tab are all in the URL
- Sharing a URL preserves the exact view state
- Navigation supports browser back/forward

**State fields** (`client/src/lib/url-state/workspace.ts`):
- `tab` — `explorer` (default) | `radar`
- `selected` — selected notice ID
- `q` — search text
- `status` — official status
- `stage` — derived stage
- `region` — buyer region
- `category` — primary category
- `publication_from` / `publication_to` — publication date range
- `close_from` / `close_to` — close date range
- `min_amount` / `max_amount` — amount range
- `procurement_type` — procurement type filter
- `less_than_100_utm` — boolean flag
- `page` / `page_size` — pagination
- `sort_by` / `sort_order` — sorting

Default state: `{tab: "explorer", page: 1, pageSize: 20, sortBy: "close_date", sortOrder: "asc"}`

---

## 8. Design System & Visual Language

### 8.1 Color Tokens (from `tokens.css`)

All colors use `oklch()` for consistent perceptual uniformity.

| Token | Usage | Hue Family |
|---|---|---|
| `--background-app` | Page background | Cool gray-blue |
| `--background-surface` | Card/panel background | Near-white |
| `--background-elevated` | Elevated surface | Light gray |
| `--background-hover` | Hover state | Subtle warm gray |
| `--text-primary` | Primary text | Dark navy (oklch 0.22) |
| `--text-secondary` | Secondary text | Medium gray (oklch 0.35) |
| `--text-muted` | Muted/helper text | Gray (oklch 0.52) |
| `--accent` | Primary action/accent | Deep blue-violet (oklch 0.43/0.105) |
| `--accent-soft` | Accent background | Light blue-violet |
| `--status-open` | Open stage | Green (oklch 0.38/0.09/155) |
| `--status-closing-soon` | Closing soon stage | Amber (oklch 0.45/0.12/55) |
| `--status-closed` | Closed stage | Dark neutral (oklch 0.38/0.025/255) |
| `--status-awarded` | Awarded stage | Deep blue (oklch 0.45/0.14/255) |
| `--status-risk` | Risk/revoked stage | Red (oklch 0.34/0.13/25) |
| `--focus-ring` | Keyboard focus | Bright blue-violet |

### 8.2 Component Visual Patterns

- **Cards**: Rounded corners (8px), subtle border, background gradient, box-shadow panel shadow
- **Chips/Badges**: Full-round (999px border-radius), colored borders, compact padding
- **Buttons**: 2.4rem min-height, 4px border-radius, ghost/primary variants
- **Tables**: Sticky header, `--background-table-head`, min-width 1120px for horizontal scroll
- **Detail drawer**: Sticky right panel, slide-in animation (220ms ease-out), popover-level shadow
- **Upload sheet**: Fixed overlay from right, terminal-style console with animated pips
- **KPI chips**: Pill-shaped with colored left-border status indicator
- **Status chips**: Small roundel badges with stage-specific colors
- **Skeletons**: Shimmer effect for loading states
- **Error states**: Red-bordered containers with warning icon

### 8.3 Typography & Spacing

- All text uses system font stack via Tailwind
- Kicker: 0.76rem uppercase bold
- Title: 2.2rem bold with tight letter-spacing
- Body: 0.86rem-0.92rem
- Labels/muted: 0.72rem-0.82rem
- Numeric/tabular: `font-variant-numeric: tabular-nums`
- Grid-based layout with CSS Grid in workspace.css
- Spacing units: 0.45rem, 0.65rem, 0.75rem, 0.85rem, 1rem, 1.25rem

### 8.4 Animation & Interaction

- Detail drawer: `detail-slide-in` animation (220ms ease-out)
- Card hover: translateY(-1px) + enhanced shadow (140ms)
- Upload progress: CSS transition (220ms ease) + animated pips
- Focus-visible: 2px outline ring with offset
- No heavy animations; transitions are 120-220ms

---

## 9. Display Labels Mapping

All user-facing labels are in Chilean Spanish. The mapping between backend field names and UI labels is:

| Backend/API Field | UI Label | Context |
|---|---|---|
| `noticeId` | Internal ID (not shown) | — |
| `externalNoticeCode` | `Código` | Code column, detail header |
| `title` | `Título` | Title column, detail |
| `officialStatus` | `Estado oficial` | Status column, filter, detail |
| `derivedStage` | `Etapa` | Stage badge, filter |
| `estimatedAmount` | `Monto estimado` | Amount column, detail |
| `currencyCode` | Currency suffix | Money formatting |
| `publicationDate` | `Publicado` / `Fecha de publicación` | Date column, filter, detail |
| `closeDate` | `Cierre` / `Fecha de cierre` | Date column, filter, detail |
| `daysRemaining` | `Días restantes` | Days column |
| `buyerName` | `Comprador` | Buyer column, detail |
| `buyerRegion` | `Región` | Region column, filter |
| `primaryCategory` | `Categoría` | Category column, filter |
| `procurementType` | `Tipo licitación` | Procurement type |
| `isLessThan100Utm` | `Menor a 100 UTM` | Filter checkbox |
| `lineCount` | `Líneas` | Evidence chip |
| `bidCount` / `supplierCount` | `Ofertas` / `Proveedores` | Evidence chips |
| `purchaseOrderCount` | `Órdenes de compra` | Evidence chip |
| `relationshipCertainty` | `Certeza` | Relationship label |

**Stage labels** (from `display-contract.ts`):
| Stage Value | UI Label |
|---|---|
| `open` | `Abierta` |
| `closing_soon` | `Cierra pronto` |
| `closed` | `Cerrada` |
| `awarded` | `Adjudicada` |
| `revoked_or_suspended` | `Revocada o suspendida` |
| `unknown` | `Sin clasificar` |

**Relationship certainty labels**:
| Value | UI Label |
|---|---|
| `high` | `Alta` |
| `medium` | `Media` |
| `low` | `Baja` |
| `none` | `Sin evidencia` |
| `unconfirmed` | `No confirmada` |

**Procurement type labels**:
| Value | UI Label |
|---|---|
| `public` | `Pública` |
| `private` | `Privada` |
| `service` | `Servicios` |

**Fallback for unavailable data**: `No disponible`

---

## 10. ChileCompra External Link

The detail pane constructs external links to ChileCompra using:
```
https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion={externalNoticeCode}
```

---

## 11. Planned Upgrades (Decision-First — Not Yet Implemented)

The following is **planned but not yet implemented**. The current video will NOT show these features. They are documented here so the analysis agent can identify gaps between current state and planned state.

### 11.1 Decision-First Information Architecture

**Current**: Explorer (table) + Radar (Kanban) views with filters
**Planned**: `Lista` (scan-first list) as default view, plus `Tabla` (table) and `Radar` (board)

Key planned changes:
- Reframe header as "decision header" with urgency KPIs: abiertas, cierran pronto, monto relevante, en radar, sin revisar
- Reduce cognitive load by surfacing urgency context first
- Separate data operations (upload, ingestion) into dedicated `Centro de Ingesta` surface instead of being mixed into the main workspace

### 11.2 Evidence-Package Detail Drawer

**Current**: Raw data tabs (lines, offers, purchase orders)
**Planned**: Structured evidence package with:
- Executive summary
- "Why this opportunity matters now" section
- Key dates timeline
- Buyer history snapshot (when data exists)
- Compatibility signals (deterministic rules, not predictions)
- Human bid/no-bid checklist
- Explicit human-review disclaimer

### 11.3 Supplier Profile Compatibility Signals

**Current**: No supplier profile or compatibility features
**Planned**: User-provided supplier profile (rubros, regions, products/ONU codes, amount range, restrictions) matched deterministically against opportunity fields to produce compatibility signals:
- `Producto compatible` — category/ONU overlap
- `Región compatible` — region match
- `Monto en rango` — amount within range
- `Cierre dentro de ventana` — close date within readiness window
- `Falta dato clave` — required field is null

All signals expose source field(s), rule applied, and result state (`compatible`, `warning`, `incompatible`, `unknown`). No predictive scores persisted.

### 11.4 Compra Ágil Lane

**Current**: No Compra Ágil-specific view
**Planned**: Dedicated tab/lane for agile purchase opportunities derived from `is_agile_purchase_flag` / `es_compra_agil` data (>980K records available). Source-specific filters and urgency model.

### 11.5 Buyer Intelligence Snapshot

**Current**: Basic buyer name/region in detail
**Planned**: Deterministic buyer history when sufficient data exists:
- Comparable notices count
- Typical awarded/estimated amount band
- Average bid/supplier competition
- Notice-to-PO materialization rate
- Recurring supplier presence

### 11.6 Action Semantics

**Current**: Selection opens detail, copy code, open external link
**Planned**:
- Primary: `Analizar oportunidad` (Analyze opportunity)
- Secondary: `Agregar al radar` (Add to radar), `Ver fuente` (View source), `Descartar` (Discard — local session only in MVP)

---

## 12. What the Agent Should See in the Video

When analyzing a video capture of the current `/licitaciones` workspace, expect to see:

1. **Header area**: Dark gradient banner with "Oportunidades" title, "Licitaciones" badge, KPI metric chips (Abiertas, Cierran pronto, Adjudicadas, Monto total), data freshness indicator, and "Centro de Ingesta" button

2. **Filter area**: Search input with magnifying glass icon, dropdown filters for Status, Stage, Region, Category, dates; collapsible advanced section; active filter chips row; Refresh and Clear buttons

3. **Toolbar**: Tab pills ("Lista" / "Radar"), result count text, sort selector, watchlist toggle, pagination

4. **View area** (one at a time):
   - **Explorer/Table view**: Full data table with columns for star, code, title, status, stage, buyer, region, publication date, close date, days remaining, amount. Clickable rows. Expandable row detail panels.
   - **Radar/Board view**: Six Kanban columns (Abierta, Cierra pronto, Cerrada, Adjudicada, Revocada o suspendida, Sin clasificar) with opportunity cards

5. **Detail pane** (when row/card selected): Sticky right panel with close button, notice code, status badges, action buttons (Copiar código, Abrir licitación), and detail sections for summary, timeline, buyer info, lines, offers, purchase orders

6. **Upload sheet** (when triggered): Full-screen overlay with dataset selector, CSV dropzone, three-step workflow (Preparar → Validar → Cargar), animated progress console

7. **Empty/loading/error states**: Skeleton placeholders, "No se encontraron oportunidades" messages, error states with HTTP codes

---

## 13. Key UX Patterns to Evaluate

When analyzing the video, focus on:

1. **Decision urgency**: Does the first viewport immediately answer "what should I review today?"
2. **Scanability**: Can a user scan the list/table and understand opportunity status in <5 seconds?
3. **Filtering flow**: Is the filter → result → refine cycle smooth?
4. **Evidence access**: Does the detail pane provide decision-relevant information quickly?
5. **Watchlist/use tracking**: Is it easy to mark and return to important opportunities?
6. **Upload/data flow separation**: Is the CSV ingestion flow clearly separated from opportunity review?
7. **Stage color coding**: Are the stage-specific colors intuitive and consistent?
8. **Mobile responsiveness**: (Not yet documented as implemented)
9. **Accessibility**: Focus ring visibility, keyboard navigation, ARIA roles
10. **Spanish language consistency**: Are all labels properly accented and using domain terms?

---

## 14. Known Limitations (Current Implementation)

- No supplier profile or compatibility signals
- No Compra Ágil dedicated lane
- No buyer intelligence snapshot
- No decision checklist or bid/no-bid support
- Watchlist is client-side only (localStorage)
- No persistent user sessions or authentication
- No AI/NLP features
- Upload workflow is manual CSV only
- Mobile responsiveness not explicitly documented
- Infinite scroll is implemented but pagination controls also visible
- Detail pane width is fixed (340-440px) and may clip on narrow viewports

---

## 15. File Reference Index

For quick lookup when the agent needs to cross-reference code:

| File | Purpose |
|---|---|
| `client/src/features/opportunity-workspace/workspace.tsx` | Main workspace component (2131 lines) |
| `client/src/features/opportunity-workspace/workspace-list-views.tsx` | Explorer table + Radar board |
| `client/src/features/opportunity-workspace/workspace-detail-pane.tsx` | Detail drawer component |
| `client/src/features/opportunity-workspace/display-contract.ts` | UI label mappings |
| `client/src/features/opportunity-workspace/query-state.ts` | URL state management hook |
| `client/src/features/opportunity-workspace/upload-workflow-state.ts` | Upload flow state machine |
| `client/src/lib/api/opportunities.ts` | API client functions |
| `client/src/lib/api/http.ts` | HTTP client (fetch wrapper) |
| `client/src/lib/api/manual-uploads.ts` | Upload API client |
| `client/src/lib/url-state/workspace.ts` | URL serialization/deserialization |
| `client/src/lib/formatters/opportunities.ts` | Display formatting (dates, money, counts) |
| `client/src/types/opportunities.ts` | TypeScript type definitions |
| `client/src/styles/tokens.css` | Design tokens (colors, radii, shadows) |
| `client/src/styles/workspace.css` | Workspace-specific CSS (~2488 lines) |
| `backend/api/routers/opportunities.py` | API endpoint handlers |
| `backend/api/opportunities_contract.py` | Pydantic response models |
| `backend/api/opportunities_query.py` | SQL query builders |
| `backend/models/normalized.py` | Data models (Normalized + Silver) |
| `backend/models/operational.py` | Operational models (SourceFile, PipelineRun, etc.) |
| `backend/models/raw.py` | Raw ingestion models |
## Context

Omnibid already exposes a read-only opportunity workspace, manual upload flow, and a compact set of operational read contracts. The north-star mockups add more surface area, but the implementation must still be grounded in the current repo truth:

- opportunity read endpoints already expose list, summary, and detail evidence
- operational endpoints already expose runs, files, and dataset summary snapshots
- manual upload jobs already expose progress, telemetry, and lineage
- the codebase already treats Silver as deterministic fact storage, not a prediction layer

The new screenshots are visual north stars only. They are not contracts. The design must therefore start from an availability audit and only then choose which surfaces become real.

```text
/licitaciones
  ├─ Lista
  ├─ Tabla
  ├─ Priorización
  └─ Seguimiento
        └─ detail drawer

/ingesta
  ├─ Visión general
  ├─ Carga CSV
  ├─ Llamadas API
  ├─ Logs y monitoreo
  └─ Historial
```

## Goals / Non-Goals

**Goals:**
- keep the workspace read-only and Spanish-first
- make the first viewport answer what to review now and why
- preserve the current `/licitaciones` and `/opportunities` compatibility
- reuse current data where possible before asking for backend work
- expose explicit availability states instead of implied certainty
- keep ingestion diagnostics separate from commercial triage

**Non-Goals:**
- predictive scoring or ranking as business truth
- mutating workflow actions in the opportunity workspace
- one-shot rewrite of the full app
- public SEO or public-facing procurement catalog work
- documents/bases/anexos claims unless the audit proves a source-backed path

## Decisions

1. **One product shell, three surfaces.**
   - Keep one shared UI system and two major user surfaces: opportunity review and ingestion operations.
   - Alternative considered: a full app rewrite or a new standalone app shell.
   - Rejected because it increases blast radius and makes data gaps harder to isolate.

2. **`Lista` and `Tabla` are view modes over the same data, not separate datasets.**
   - This keeps filter state, selection, and evidence consistent.
   - Alternative considered: duplicate data queries and independent table logic.
   - Rejected because it invites drift and makes the same fact look different in different views.

3. **`Priorización` is deterministic, not predictive.**
   - Buckets can be derived from existing dates, amounts, status, watchlist state, and source flags.
   - Alternative considered: expose a numeric score or ranking model.
   - Rejected because Silver must not become a prediction layer.

4. **`Seguimiento` starts as local state.**
   - Use the existing local watchlist behavior until a separate persisted follow-up contract exists.
   - Alternative considered: introduce persistence now.
   - Rejected because it would couple this redesign to a new write workflow.

5. **The detail experience stays evidence-first and drawer-based for v1.**
   - The current drawer already packages the right evidence shape; the redesign should refine, not replace, the review mechanics.
   - Alternative considered: immediate full-page detail replacement.
   - Rejected because the current interaction model already supports fast review and preserves context.

6. **Ingestion diagnostics are source-backed only.**
   - Runs, files, telemetry, and lineage are shown only when the data is present in the repo or an explicit read-only extension is added.
   - Alternative considered: show live worker, live latency, and live logs with synthetic estimates.
   - Rejected because that would blur the line between persisted facts and operational inference.

7. **Ingestion mutability is limited to the current CSV upload contract.**
   - `/ingesta` may expose the existing manual CSV lifecycle: file selection, preflight validation, process trigger, and job polling.
   - Alternative considered: implement the screenshot's broader operational controls (`Ejecutar sincronización`, `Programar`, `Reprocesar`, `Reejecutar`, retry, notes, schedule editing, endpoint creation).
   - Rejected because those are new write/orchestration workflows and must not be smuggled into this read-first redesign.

8. **Unsupported fields must stay visibly unsupported.**
   - Missing documents, bases, anexos, or advanced trend signals should render an explicit unavailable state.
   - Alternative considered: hide the gaps or replace them with vague copy.
   - Rejected because the product must remain evidence-first.

9. **`Decision Brief` and `Por qué revisar` are not v1 generated content.**
   - v1 may reserve the section with `Sin dato — requiere contrato de síntesis determinística`.
   - Alternative considered: generate narrative copy from current facts immediately.
   - Rejected because narrative synthesis can sound authoritative before provenance, wording rules, and tests exist.

10. **The quick-analysis rail is future analytics, not v1 scope.**
   - The `Competencia esperada`, `Historial de adjudicación`, `Tiempo promedio de adjudicación`, and `Ahorro promedio histórico` chips are analytical readouts, not core review facts.
   - Alternative considered: surface them directly from the detail drawer in v1.
   - Rejected because they need an explicit analytics contract and could otherwise be mistaken for source-backed certainty.

11. **Architecture screenshot navigation is future context, not v1 scope.**
   - v1 sidebar exposes only `Oportunidades` and `Centro de Ingesta`.
   - Any broader entries from the architecture reference are disabled placeholders or omitted entirely until a dedicated proposal owns them.

12. **KPI cards are deliberately conservative.**
   - v1 ships only direct counts, sums, and existing summary metrics that can be sourced without inventing trend baselines or alert semantics.
   - Alternative considered: mirror every screenshot KPI chip exactly.
   - Rejected because it would force ambiguous counts like `Nuevas hoy`, `Cambios hoy`, or `Alertas activas` into v1 without a stable contract.

13. **Missing data uses two different fallback behaviors.**
   - If the product concept does not exist in v1, the whole section stays unavailable or omitted.
   - If the contract exists but a given record lacks a field, the UI renders `Sin dato` in cards and drawers, and `-` only in dense table cells where compact scanability matters more than prose.
   - Alternative considered: use one placeholder for everything.
   - Rejected because concept-level absence and record-level optionality are different user problems.

14. **History is a bounded moving window, not an infinite list.**
   - `Historial` and recent-activity surfaces should default to an explicit range such as the latest executions or a visible date window.
   - Alternative considered: an unbounded feed of all past events.
   - Rejected because bounded windows are easier to read, easier to verify, and less likely to imply completeness we do not have.

15. **Day-window KPIs stay out of v1 unless the window is explicit.**
   - `Cargas hoy` is not part of v1 because its meaning depends on a time window that must be labeled in the UI and contract.
   - Alternative considered: ship it with an implied "today" semantics.
   - Rejected because the label would be easy to read but still too easy to implement inconsistently.

## Risks / Trade-offs

- [Risk] A richer UI can become a dashboard blob if hierarchy is weak.
  - Mitigation: keep the shell compact, use progressive disclosure, and preserve one main triage path.

- [Risk] `Decision Brief` and `Why review` can sound factual even when they are synthesis.
  - Mitigation: do not generate them in v1; render a clear future/unavailable state until a deterministic synthesis contract exists.

- [Risk] The redesign can outgrow the current backend contracts.
  - Mitigation: keep the audit authoritative and add backend extensions only for source-backed gaps.

- [Risk] Ingestion logs and API diagnostics can swallow the opportunity workspace.
  - Mitigation: isolate them in `Ingestion Center` and keep `/licitaciones` focused on review.

- [Risk] `Prioridad` can be mistaken for a predictive score.
  - Mitigation: use deterministic bucket labels and avoid numeric score semantics in the workspace.

- [Risk] The prioritization north-star can be mistaken for an editable score editor.
  - Mitigation: keep v1 limited to urgency buckets, hide score ordering, and defer the criteria rail until a separate Gold-backed contract exists.

## Migration Plan

1. Freeze the availability audit and classify every mockup element.
2. Build the shared UI system and app shell without changing contracts.
3. Rework `/licitaciones` into `Lista`, `Tabla`, `Priorización`, `Seguimiento`, and detail.
4. Add the ingestion center as a separate operational surface.
5. Add backend read-only extensions only for fields that the audit marks as missing but necessary.
6. Validate with targeted frontend/backend tests and OpenSpec checks.

Rollback:
- keep the current workspace entry points available while the new surfaces are being built
- if a section cannot be sourced, fall back to an explicit unavailable state rather than a broken or fake UI
- do not remove the current read contracts until the new view can read the same facts cleanly

## Per-View Component Tree

### Opportunity Workspace

**Lista:**
KPI strip (summary metrics) → filter bar (search + primary/advanced filters) → sort chips → scan rows (título, código, estado, tipo, comprador, región, fechas, monto, días restantes, categoría, badges, evidencia) → detail drawer trigger.

**Tabla:**
Same data as Lista, presented as a dense columnar table with selectable/sortable columns. Actions column triggers detail drawer.

**Priorización:**
Kanban or bucket columns with deterministic labels (no numeric scores). Each card shows the same scan fields as Lista. Cards can be moved to `Seguimiento` bucket (local only). The weighted criteria rail shown in the north-star is deferred and does not ship in v1.

**Seguimiento:**
Local watchlist filtered list. Same row presentation as Lista. Empty state with copy explaining local-session scope. Screenshot elements that imply persisted monitoring (`Cambios hoy`, `Alertas activas`, trend sparklines, alert configuration, upcoming-deadline automation) remain unavailable unless backed by a later daily snapshot or alert contract.

**Detalle completo:**
Header (código, estado oficial, etapa derivada) → timeline (publicación, cierre, adjudicación estimada, adjudicación) → evidencia (líneas, ofertas, órdenes de compra con counts y relación) → buyer snapshot (nombre, región, comuna, unidad de contratación) → documentos placeholder (`Sin dato`) → actividad reciente en una ventana acotada y explícita.

### Ingestion Center

**Visión general:**
KPI cards (ejecuciones recientes, archivos, snapshot freshness) → tabla de últimas ejecuciones → resumen de datasets.

**Carga CSV:**
Upload dropzone → file info → preflight panel (validación de esquema, hash, duplicados) → progress bar → job telemetry (filas procesadas, aceptadas, rechazadas) → historial de jobs.

Allowed mutations: selecting a CSV, preflight validation, processing that staged CSV through the existing endpoint, and polling the resulting job. Not allowed in this proposal: scheduled imports, API sync execution, replay/reprocess/retry controls, notes, endpoint creation, or schedule editing.

**Llamadas API:**
KPI cards (llamadas hoy, rate limit, último status) → tabla de requests recientes → payload viewer (si disponible).

**Logs y monitoreo:**
Log stream (si endpoint existe) → errores activos (con ventana de tiempo) → worker status (`Sin dato` si no hay runtime visibility) → queue state.

**Historial:**
Tabla de runs con expand para steps, batches y lineage → file hash → payload → incidencias → notas operativas (`Sin dato` si no existe campo). El historial debe ser una ventana acotada con rango visible, no una lista infinita.

## Responsive

Desktop-first only for Phase 1-6 (1920px → 1280px). Responsive/mobile remains a later phase after the desktop experience reaches parity with current workspace functionality.

## Sidebar

Defined in Phase 1 (UI system). The global sidebar provides two top-level entries: `Oportunidades` (`/licitaciones`) and `Centro de Ingesta` (`/ingesta`). The sidebar is shared across both surfaces. Broader architecture-reference entries (`Contratos`, `Proveedores`, `Reportes`, `Alertas`, `Integraciones`, `Configuración`) are not v1 navigation and must be omitted or visibly disabled as future placeholders.

## Open Questions (Resolved)

- **Should the ingestion center be a dedicated route or a nested route under the workspace shell?**
  → Dedicated route (`/ingesta`). Keeps clear separation and prevents log/upload UI from competing with commercial triage in `/licitaciones`.

- **Which `Priorización` buckets should ship in v1: only urgency buckets, or urgency plus buyer/category fit buckets?**
  → Only urgency buckets in v1: "Revisar hoy" (cierre ≤2 días), "Cierra esta semana" (cierre ≤7 días), "Abierta con plazo", "En radar". Fit buckets require a supplier profile contract (`opportunity-workspace-decision-first-upgrade`) and are deferred.

- **Should the weighted criteria rail / score editor shown in the north-star ship in v1?**
  → No. v1 ships urgency buckets only; the criteria rail stays deferred until a separate Gold-backed scoring contract exists.

- **Can documents/bases/anexos be sourced from existing API or snapshot data, or do they require a new document ingestion path?**
  → Require a new document registry and ingestion path. No endpoint or table exists for documents/bases/anexos today. Rendered as `Sin dato — requiere registro documental futuro` in v1.

- **Should the API contract extensions be limited to summary metrics, or should they also expose direct request-ledger views for diagnostics?**
  → Summary metrics first (counts by day, status aggregates). Direct request-ledger with individual payload inspection requires a new endpoint and is deferred to Phase 6+.

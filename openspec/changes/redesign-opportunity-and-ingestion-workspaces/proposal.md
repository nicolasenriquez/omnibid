## Why

Omnibid already has a read-only opportunity workspace and operational ingestion endpoints, but the new north-star mockups require a broader information architecture: a scan-first opportunity workspace, a dedicated ingestion center, and a shared UI system. The change must start with a data-availability audit so the redesign does not invent fields, tables, endpoints, or workflows that the repo cannot actually support.

This proposal is discovery-first on purpose. The goal is not to ship a visual rewrite in one pass, but to produce an auditable plan that separates what exists today, what can be derived from current facts, and what would require backend or future Gold work.

## What Changes

- Reframe the product into three coordinated surfaces:
  - `Opportunity Workspace` for review and triage.
  - `Ingestion Center` for operational intake and diagnostics.
  - `UI System` for shared scan-density components and states.
- Keep `/licitaciones` and `/opportunities` compatible, but reshape their presentation into a multi-view read-only workspace with explicit availability states.
- Add an incremental path for `Lista`, `Tabla`, `Priorización`, `Seguimiento`, and full detail, instead of replacing the whole app at once.
- Separate commercial review from technical ingestion so logs, runs, and upload diagnostics stop competing with opportunity triage.
- Add backend contract work only where the audit proves the data exists but is not yet exposed, or where a read-only derived view is needed.
- Keep unsupported signals visible as unavailable rather than silent, implied, or fabricated.

## Scope

In scope:
- discovery-first audit of current frontend, backend, models, docs, and screenshots
- workspace redesign around existing read-only facts
- ingestion center redesign around existing operational lineage
- shared UI components and availability states
- minimal read-only backend contract extensions only when justified by the audit

Out of scope:
- predictive scoring
- autonomous recommendations
- write workflows for assignments, notes, reminders, or persistent discard actions
- public SEO or public-facing routing
- full mobile redesign as a first slice
- KPI cards or rails that require trend baselines, alert semantics, or narrative analytics in v1 (`Nuevas hoy`, `Cambios hoy`, `Alertas activas`, `Próximos vencimientos`, quick-analysis rail, `Errores activos` unless explicitly defined as a plain count)
- broad sidebar destinations shown in the architecture screenshots (`Contratos`, `Proveedores`, `Reportes`, `Alertas`, `Integraciones`, `Configuración`) except as disabled future placeholders
- operational orchestration controls outside the existing manual CSV upload path (`Ejecutar sincronización`, `Programar`, `Reprocesar`, `Reejecutar`, retry/replay, API endpoint creation, schedule editing)
- generated `Decision Brief`, `Por qué revisar`, or recommendation copy in v1
- any Silver field that behaves like a business prediction (`*_score`, `*_probability`, `forecast_*`, `recommendation_*`)

## Non-Goals

- Replacing the current app in one release.
- Turning the workspace into a mutable CRM-like flow.
- Claiming documents, bases, anexos, or alerts that are not backed by current contracts.
- Moving heuristic, ranking, or forecast logic into Silver.

## Principles

- Evidence first: every visible state must map to a source-backed fact or an explicit unavailable state.
- Deterministic only: any prioritization or synthesis must be explainable from current fields.
- Spanish first: all user-facing labels remain in Spanish procurement language.
- Read-only first: the workspace must not imply persistence or authority that does not exist.
- KPI minimalism: keep only direct counts, sums, or existing summary metrics in v1; anything that needs a trend baseline, alert window, or narrative interpretation must stay unavailable until a dedicated read model exists. Day-window KPIs like `Cargas hoy` stay out of v1 until the window is explicitly labeled and backed by a dedicated contract.
- Missing-data policy: hide a whole section only when the concept is not modeled in v1; if a field is supported but absent for a specific record, render `Sin dato` in cards and drawers, and use `-` only in dense table cells when compact scanability is more important than prose.
- Incremental by design: each phase must be shippable and testable on its own.
- Data-availability gating: each mockup element must be classified before implementation.

## Incremental Strategy

- Phase 0: discovery and audit.
- Phase 1: shared UI system and app shell.
- Phase 2: Opportunity Workspace v1 using current facts.
- Phase 3: deterministic Priorización and Seguimiento.
- Phase 4: full detail packaging with explicit availability states.
- Phase 5: Ingestion Center v1 — overview and CSV upload.
- Phase 6: Ingestion Center v1 — API diagnostics, logs, and history.
- Phase 7: backend/API extensions only where the audit justifies them.
- Phase 8: tests, docs, and validation.

## Compatibility

- Keep `/licitaciones` as the main user entry point.
- Keep `/opportunities` and the current opportunity read contracts compatible.
- Preserve the current local watchlist behavior until a separate persistence change exists.
- Preserve the current read-only posture for the opportunity workspace.
- Keep Ingestion Center operator-controlled only for the existing manual CSV upload lifecycle (`preflight` -> `process` -> `job polling`). All API scheduling, replay, retry, reprocess, notes, and orchestration controls remain unavailable or out of scope unless a separate write contract is proposed.
- If a field is unavailable, render `Sin dato` or an equivalent explicit unavailable state instead of a fabricated placeholder.
- The `data-availability-audit.md` is the authoritative gate for implementation: no mockup field may be implemented without a prior classification row in the audit matrix.
- During transition, the current workspace views (`Explorador`, `Radar`) coexist with the new views (`Lista`, `Tabla`, `Priorización`, `Seguimiento`) until each new view reaches functional parity and the old views can be safely deprecated.

## Capabilities

### New Capabilities
- `ingestion-center`: dedicated operational surface for CSV intake, API sync visibility, logs, bounded history windows, and reproducibility.
- `ui-system`: shared components and state vocabulary for KPI cards, badges, chips, tables, side panels, timelines, progress rows, and empty states.
- `api-contracts`: read-only backend contract extensions for source-backed KPIs, operational lineage, and explicit availability states when current endpoints are not enough.

### Modified Capabilities

- `opportunity-workspace`: modifies the existing `/licitaciones` read-only workspace into scan-first `Lista`, `Tabla`, `Priorización`, `Seguimiento`, and evidence-first detail surfaces while preserving current `/opportunities` contracts and compatibility.

## Impact

- `client/app/licitaciones/`
- `client/app/ingesta/` or equivalent route selected during implementation
- `client/src/features/opportunity-workspace/`
- likely new `client/src/features/ingestion-center/`
- `client/src/components/ui/`
- `client/src/styles/`
- `client/src/lib/`
- `client/src/types/`
- `backend/api/routers/opportunities.py`
- `backend/api/opportunities_contract.py`
- `backend/api/opportunities_query.py`
- `backend/api/routers/manual_uploads.py`
- `backend/api/routers/operations.py`
- `backend/models/operational.py`
- `backend/models/api_source.py`
- `backend/models/raw.py`
- `backend/models/normalized.py`
- `backend/models/ingestion_jobs.py`
- `docs/`
- `openspec/changes/redesign-opportunity-and-ingestion-workspaces/`

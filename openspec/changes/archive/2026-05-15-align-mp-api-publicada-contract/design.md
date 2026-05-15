# Design: Mercado Público API Publicada Contract Alignment

## Context

The existing Mercado Público pipeline already preserves the raw API payload, parses nested discovery/detail structures, and builds normalized and Silver outputs. The failure is downstream of raw persistence: the public contract still mixes official Mercado Público terminology with historical pipeline semantics, and the Silver refresh still hardcodes many fields that the API already provides.

The core business distinction is now clear:

- `Publicada` is a current opportunity state.
- `Cerrada`, `Desierta`, `Adjudicada`, `Revocada`, and `Suspendida` are later lifecycle states.
- `estado=activas` is the official discovery view for licitaciones publicadas al día de consulta.
- `Informada` changes how offers are received, and therefore changes what the pipeline should expect to see in the portal.

## Goals / Non-Goals

**Goals:**

- Use the official Mercado Público terminology as the canonical public contract.
- Treat `Publicada` as the discovery state for current opportunities.
- Parse and propagate the official JSON fields that Mercado Público already publishes.
- Keep `payload_json` as the lossless source of truth.
- Make Silver and `/opportunities` lifecycle-aware.
- Keep historical CSV behavior intact.
- Add `source_view=publicadas` as a discovery filter.
- Add a minimal `Publicadas / Activas` filter/tab in the client with lifecycle-aware labels.

**Non-Goals:**

- Creating bids, awards, suppliers, or purchase orders for `Publicada` licitaciones.
- Replacing the historical CSV model.
- Introducing a second public naming scheme for Mercado Público fields.
- Rebuilding the full domain model when the existing read model can be extended.

## Decisions

### 1. Official Mercado Público terminology is canonical

The public contract should use the same terminology that Mercado Público uses in the payloads and documentation:

- `Publicada`, `Cerrada`, `Desierta`, `Adjudicada`, `Revocada`, `Suspendida`
- `CodigoEstado`, `Estado`
- `CodigoTipo`, `Tipo`, `TipoConvocatoria`
- `Informada`
- `VisibilidadMonto`
- `FuenteFinanciamiento`

The proposal should not introduce English or project-specific public labels for these concepts. If the implementation needs helper names internally, they remain an implementation detail and do not define the domain contract.

### 2. `estado=activas` maps to `Publicada`

For user-facing discovery, `estado=activas` means the user is asking for licitaciones published as current opportunities. The read model should store and expose the official state as `Publicada` and may label the tab as `Publicadas / Activas`.

### 3. Raw payload is the source of truth; snapshot is an index layer

`payload_json` remains the lossless payload store. Snapshot rows are an index/search layer and a convenience layer for the read model, but they are not the canonical contract. When a public field exists in the API payload, the pipeline should not lose it just because the Silver builder currently reads from a narrower path.

### 4. Lifecycle-pending data must be explicit

For `Publicada`, missing bids, awards, and purchase orders are expected lifecycle-pending facts, not pipeline failures. The read model should distinguish:

- `available`
- `not_yet_public`
- `not_applicable`
- `not_reported_by_source`
- `pipeline_missing`

Those values are derived metadata, not replacements for the actual field values.

### 5. `Informada` changes availability expectations

An `Informada` licitación is public in Mercado Público, but offers are received outside the portal. That means the contract should not assume that portal-native offer data must exist for every public opportunity.

### 6. `source_view=publicadas` is additive

`source_view=publicadas` is a discovery filter for the opportunity workspace. It should not replace the existing historical CSV filters. It should return API-sourced `Publicada` opportunities and keep the existing `derivedStage` behavior backward-compatible.

### 7. API licitación coverage is exhaustive, not the full procurement lifecycle

The API contract should fully cover the licitación families that belong to current/public opportunities:

- licitación root fields
- buyer fields under `Comprador`
- date fields under `Fechas`
- item fields under `Items/Listado/item`
- adjudication fields when present

The API contract should preserve, but not invent, post-award and CSV-derived entities such as purchase orders or other historical transaction facts.

## Risks / Trade-offs

- **Terminology drift**: if the public contract keeps any legacy naming, users will continue to see a split vocabulary. Mitigation: rewrite the proposal and the implementation contract to use official Mercado Público terms consistently.
- **Open tender expectations**: if lifecycle-pending facts are not labeled explicitly, the UI will continue to suggest missing data where the process simply has not matured yet. Mitigation: derive availability metadata from state and source mode.
- **Compatibility pressure**: the historical CSV contract must stay intact. Mitigation: add the new metadata alongside existing fields instead of replacing them.

## Migration Plan

1. Align the parser and read contract to the official Mercado Público terms.
2. Update Silver refresh to use available snapshot-enriched data.
3. Add official state metadata and availability context to Silver.
4. Extend the opportunities API contract and query filters.
5. Update the client filter and labels.
6. Add focused tests for official terminology, lifecycle semantics, and API-only `Publicada` discovery.

## Open Questions

None.

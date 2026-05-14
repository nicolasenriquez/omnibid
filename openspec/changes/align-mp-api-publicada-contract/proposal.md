# Align Mercado Público API Publicada Contract

## Why

Omnibid already ingests Mercado Público API payloads, preserves the raw JSON, and enriches snapshot data with nested fields such as `Comprador`, `Fechas`, `Items` and `Adjudicacion` when they are available. The remaining problem is not raw ingestion capacity. The problem is that the public contract exposed by the read model still mixes official Mercado Público terminology with legacy pipeline terminology, and it treats a licitación `Publicada` as if it were an incomplete historical record.

Mercado Público defines the official licitación states as:

- `Publicada = 5`
- `Cerrada = 6`
- `Desierta = 7`
- `Adjudicada = 8`
- `Revocada = 18`
- `Suspendida = 19`

The same documentation also distinguishes:

- `CodigoTipo` for the type of licitación source
- `Tipo` for the tender type code, such as `L1`, `LE`, `LP`, `LQ`, `LR`, `E2`, `CO`, `B2`, `H2`, `I2`, `LS`
- `TipoConvocatoria` for `1 = Abierto` and `0 = Cerrada`
- `Informada` for processes that are public in Mercado Público but receive offers outside the portal

For discovery, Mercado Público also documents `estado=activas`, which returns licitaciones publicadas al día de consulta. For Omnibid, that means the user-facing discovery workspace should say `Publicadas / Activas`, while the stored official state remains `Publicada`.

## Problem

The current API read path still collapses three distinct cases into the same surface:

1. Fields that are present in the API payload but do not reach the read model because the Silver refresh hardcodes them as `None` or `False`.
2. Fields that are not yet public because the licitación is still `Publicada`.
3. Fields that are truly missing because of a pipeline or contract problem.

That creates avoidable confusion in `/opportunities` and in the frontend:

- public tender metadata exists in the API JSON but does not always reach the opportunity contract,
- lifecycle-pending facts are rendered like ingestion failures,
- and the discovery view does not consistently speak in Mercado Público terminology.

This change is about correcting the data contract, not building another pipeline.

## Field Coverage Contract

The API contract is exhaustive for the licitación surface and selective for the full procurement lifecycle.

### Must propagate now

These fields belong to the public licitación surface and should be parsed and propagated whenever they appear in the API payload:

- root licitación data: `CodigoExterno`, `Nombre`, `CodigoEstado`, `Estado`, `FechaCierre`, `Descripcion`, `DiasCierreLicitacion`, `Informada`, `CodigoTipo`, `Tipo`, `TipoConvocatoria`, `Moneda`, `Etapas`, `EstadoEtapas`, `TomaRazon`, `EstadoPublicidadOfertas`, `JustificacionPublicidad`, `Contrato`, `Obras`, `CantidadReclamos`, `Estimacion`, `VisibilidadMonto`, `MontoEstimado`, `FuenteFinanciamiento`, `Modalidad`, `TipoPago`, `ProhibicionContratacion`, `SubContratacion`, `TiempoDuracionContrato`, `TipoDuracionContrato`, `JustificacionMontoEstimado`, `ExtensionPlazo`, `EsBaseTipo`, `EsRenovable`
- buyer data: `CodigoOrganismo`, `NombreOrganismo`, `RutUnidad`, `CodigoUnidad`, `NombreUnidad`, `DireccionUnidad`, `ComunaUnidad`, `RegionUnidad`, `RutUsuario`, `CodigoUsuario`, `NombreUsuario`, `CargoUsuario`
- date data: `FechaCreacion`, `FechaCierre`, `FechaInicio`, `FechaFinal`, `FechaPubRespuestas`, `FechaActoAperturaTecnica`, `FechaActoAperturaEconomica`, `FechaPublicacion`, `FechaAdjudicacion`, `FechaEstimadaAdjudicacion`, `FechaSoporteFisico`, `FechaTiempoEvaluacion`, `FechaEstimadaFirma`, `FechaVisitaTerreno`, `FechaEntregaAntecedentes`
- items: `Items/Cantidad` and `Items/Listado/item/*`, including item categories, product descriptions, units, quantities, and item-level adjudication when present
- adjudication: `Adjudicacion/*` when present, but only as lifecycle-pending or available data depending on the official state

### Preserve raw only

Fields that arrive in the payload but are not part of the current opportunity contract, or that are new/unknown to the parser, must remain in `payload_json` and be visible for drift detection.

### Out of scope for the API slice

Orders of purchase, invoice-like historical facts, and other post-award CSV-derived structures remain in the monthly CSV path. The API slice should not invent or backfill those entities.

## Capabilities

### New

- `mp-publicada-discovery`: Discover current opportunities in Mercado Público using the official `Publicada` contract and `estado=activas` semantics.
- `mp-official-state-contract`: Expose the official Mercado Público lifecycle states and field names in the read model contract.
- `mp-lifecycle-aware-availability`: Distinguish lifecycle-pending data from source-missing and pipeline-missing data in the opportunity surface.

### Modified

- `mp-api-detail-parsing`: Keep parsing the official Mercado Público fields already present in the API payload and propagate them through the read path.
- `opportunities-read-model`: Extend the opportunity response contract with official state metadata and availability context without replacing the historical CSV model.
- `client-opportunity-workspace`: Add the `Publicadas / Activas` discovery surface and lifecycle-aware labels.

## Scope

Do:

- Keep the historical CSV pipeline intact.
- Keep the current `/opportunities` endpoint and extend it.
- Treat `Publicada` as a valid opportunity state, not an incomplete historical outcome.
- Parse and propagate the official Mercado Público fields that are already present in the API JSON.
- Preserve `payload_json` as the lossless source of truth for API payloads.
- Add official state metadata to Silver and to the opportunity response contract.
- Add lifecycle-aware availability semantics so the UI can distinguish `Pendiente de publicación`, `No aplica`, `No informado por fuente`, and `No cargado`.
- Add a `source_view=publicadas` discovery filter and keep it compatible with the official `estado=activas` semantics.

Do not:

- Invent bids, suppliers, awards, or purchase orders for licitaciones `Publicada`.
- Convert the official Mercado Público terminology into a separate English or project-specific naming scheme in the public contract.
- Replace the historical CSV model with the API model.
- Over-engineer a new domain model if the existing read model can be extended safely.

## Expected Outcome

API-sourced licitaciones `Publicada` should appear in the frontend and in `/opportunities` with:

- `CodigoExterno`
- `Nombre`
- `Descripcion`
- `CodigoEstado`
- `Estado`
- `FechaPublicacion`
- `FechaCierre`
- buyer fields from `Comprador`
- `ComunaUnidad`
- `RegionUnidad`
- `CodigoTipo`
- `Tipo`
- `TipoConvocatoria`
- `Informada`
- `Moneda`
- `Estimacion`
- `MontoEstimado`
- `VisibilidadMonto`
- `FuenteFinanciamiento`
- `CantidadReclamos`
- `Fechas`
- `Items` and item categories when present
- lifecycle-aware placeholders for participants, offers, adjudication, and purchase orders

## What Changes

- Align the parser and read model to official Mercado Público terminology, including the state set and the key discovery fields that the API already publishes.
- Make the Silver refresh source-aware so it consumes available snapshot-enriched fields instead of forcing `None` or `False`.
- Add official state metadata and availability context to Silver and `/opportunities`.
- Support `source_view=publicadas` as a discovery filter for API-sourced opportunities.
- Keep `derivedStage` backward-compatible, but do not use it as the canonical business status.
- Add the minimal `Publicadas / Activas` filter/tab in the client with lifecycle-aware labels.

## Impact

- `backend/pipeline/extract/mp_api_schemas.py` - align the parsed contract to official Mercado Público keys and state terminology
- `backend/pipeline/transform/mp_api_notice_refresh.py` - source-aware Silver payload builder with official state metadata and availability context
- `backend/pipeline/transform/mp_api_read_model_bridge.py` - propagate official state and availability fields into normalized and Silver structures
- `backend/api/routers/opportunities.py` - add `source_view`, expose official state metadata, and keep lifecycle semantics explicit
- `backend/api/opportunities_contract.py` - extend response models with official state and availability metadata
- `backend/models/` - add Silver columns for official state metadata and availability context via Alembic migration
- `client/` - add the `Publicadas / Activas` filter/tab and lifecycle-aware labels

## Required Fix Steps

1. Remove the public-contract wording that treats official Mercado Público fields as secondary labels or legacy terms.
2. Update the parser contract to use the official Mercado Público keys and state set.
3. Update `build_silver_notice_payload_from_snapshot` to read available snapshot-enriched fields instead of hardcoding `None` or `False`.
4. Add an Alembic migration for official state metadata and availability context in Silver.
5. Extend canonicalization so the normalized and Silver layers carry official state fields through to `/opportunities`.
6. Add `source_view=publicadas` and preserve the backward-compatible `derivedStage` behavior.
7. Add tests for official field parsing, lifecycle-aware availability, and API-only `Publicada` discovery.
8. Add the minimal client filter and labels that speak in Mercado Público terms.

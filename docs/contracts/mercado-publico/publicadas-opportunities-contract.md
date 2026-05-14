# Mercado Público Publicadas Contract

## Purpose

This document defines the official Mercado Público contract used by Omnibid for API-sourced licitaciones and `/opportunities` discovery.

## Official Lifecycle States

The contract uses Mercado Público official state terminology and codes:

- `CodigoEstado=5` -> `Estado=Publicada`
- `CodigoEstado=6` -> `Estado=Cerrada`
- `CodigoEstado=7` -> `Estado=Desierta`
- `CodigoEstado=8` -> `Estado=Adjudicada`
- `CodigoEstado=18` -> `Estado=Revocada`
- `CodigoEstado=19` -> `Estado=Suspendida`

Read model fields:

- `mp_estado_codigo`
- `mp_estado_nombre`
- `mp_estado_canonical`

## Discovery Semantics

- Mercado Público discovery semantics for active notices are represented as `Publicadas / Activas`.
- `/opportunities?source_view=publicadas` returns only notices matching:
  - `mp_estado_canonical = 'publicada'`, or
  - `data_source_kind IN ('api_publicada', 'api_detail')`.
- `derivedStage` remains backward-compatible for existing consumers and is not the canonical business status.

## Licitación Field Contract

The `/opportunities` contract surfaces official Mercado Público licitación terminology where available:

- `CodigoTipo`
- `Tipo`
- `TipoConvocatoria`
- `Informada`
- `VisibilidadMonto`
- `FuenteFinanciamiento`

Buyer location can be sourced from API buyer data (`Comprador`) and is exposed through:

- `buyerRegion`
- `buyerCommune`

## Availability Semantics

Detail responses (`/opportunities/{notice_id}`) include:

- `participantsAvailability`
- `offersAvailability`
- `awardAvailability`
- `purchaseOrderAvailability`
- `descriptionAvailability`

Allowed values:

- `available`
- `not_yet_public`
- `not_applicable`
- `not_reported_by_source`
- `pipeline_missing`

Rules:

- For `Estado=Publicada`, missing participants/offers/adjudication/purchase orders are lifecycle-pending (`not_yet_public`), not ingestion failure.
- For `Informada`, portal-native offers/participants are not guaranteed; absent portal evidence can be `not_reported_by_source`.
- `pipeline_missing` is reserved for missing expected data outside lifecycle/source exceptions.

## Compatibility Boundary

- Historical CSV behavior remains compatible.
- API-only `Publicada` notices can appear in `/opportunities` even without normalized CSV rows.
- Unknown or non-contract payload fields remain preserved in `api_source_payload.payload_json` for drift detection and future expansion.

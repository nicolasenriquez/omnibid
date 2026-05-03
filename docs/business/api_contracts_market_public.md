# API Contracts: Mercado Publico

## Purpose
Document the operational API contract separately from the monthly CSV downloads.

## Audience
- backend and data pipeline engineers
- agents that need to refresh active opportunities or fetch detail by code

## Official sources
- [API de Mercado Publico](https://www.chilecompra.cl/api/)
- [API Licitaciones PDF](https://www.chilecompra.cl/wp-content/uploads/2026/03/Documentacion-API-Mercado-Publico-Licitaciones.pdf)
- [API OC PDF](https://www.chilecompra.cl/wp-content/uploads/2026/03/Documentacion-API-Mercado-Publico-oc.pdf)

## Shared API rules
- Access uses GET parameters and a ticket.
- Supported response formats are JSON, JSONP, and XML.
- The API is operational and query-oriented, not a batch history dump.
- Field names and legacy typologies should be preserved in technical adapters.

## Licitaciones API

### Access patterns
- by code
- by day
- by state
- by state and day
- by public buyer org
- by supplier
- `estado=activas` returns notices published at query time

### Key states

| State | Code |
|---|---|
| Publicada | 5 |
| Cerrada | 6 |
| Desierta | 7 |
| Adjudicada | 8 |
| Revocada | 18 |
| Suspendida | 19 |

### Key fields
- `CodigoExterno`
- `Nombre`
- `CodigoEstado`
- `FechaCierre`
- `Descripcion`
- `Comprador/*`
- `DiasCierreLicitacion`
- `Tipo`
- `Moneda`
- `Etapas`
- `EstadoEtapas`
- `TomaRazon`
- `EstadoPublicidadOfertas`
- `Fechas/*`
- `MontoEstimado`
- `FuenteFinanciamiento`
- `VisibilidadMonto`
- `Adjudicacion/*`
- `Items/*`

## Ordenes de Compra API

### Access patterns
- by order code
- by day
- by state
- by state and day
- by public buyer org
- by supplier

### Key states

| State | Code |
|---|---|
| Enviada a Proveedor | 4 |
| En proceso | 5 |
| Aceptada | 6 |
| Cancelada | 9 |
| Recepcion Conforme | 12 |
| Pendiente de Recepcionar | 13 |
| Recepcionada Parcialmente | 14 |
| Recepcion Conforme Incompleta | 15 |

### Key fields
- `Codigo`
- `Nombre`
- `CodigoEstado`
- `CodigoLicitacion`
- `Descripcion`
- `CodigoTipo`
- `Tipo`
- `TipoMoneda`
- `CodigoEstadoProveedor`
- `EstadoProveedor`
- `Fechas/*`
- `TieneItems`
- `TotalNeto`
- `Impuestos`
- `Total`
- `Comprador/*`
- `Proveedor/*`
- `Items/*`

## Differences from CSV downloads
- API records are easier to query by code and status.
- CSV downloads are better for historical batch processing.
- API and CSV do not guarantee the same grain or the same field names.

## Recommended use in `omnibid`
- Use the API to refresh active notices and check recent state changes.
- Use the API for point lookups and incremental enrichment.
- Use CSV downloads as the canonical historical batch source.

## Validation minima
- confirm the ticket is valid
- confirm the query parameters map to the intended resource
- confirm optional links stay optional, especially `CodigoLicitacion` in OC data
- confirm legacy states are preserved as source facts, not rewritten as product labels

## Risks
- a live operational state may differ from the latest monthly CSV
- field names can be nested and legacy
- the API can expose data that is not present in a monthly download yet

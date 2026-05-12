# mp-api-detail-parsing Specification

## Purpose
Define the Pydantic schema contract for parsing full detail-by-codigo payloads from the Mercado Publico API, including nested Comprador, Fechas, Items, and Adjudicacion sub-objects, with fallback support for summary-mode flat fields.

## ADDED Requirements

### Requirement: The parser MUST capture nested Comprador fields from detail payloads
The system SHALL parse the `Comprador` sub-object from detail-by-codigo API responses into a dedicated `CompradorPayload` model containing `CodigoOrganismo`, `NombreOrganismo`, `RutUnidad`, `CodigoUnidad`, `NombreUnidad`, `DireccionUnidad`, `ComunaUnidad`, `RegionUnidad`, `RutUsuario`, `CodigoUsuario`, `NombreUsuario`, and `CargoUsuario`.

#### Scenario: Detail payload contains nested Comprador
- **WHEN** a detail-by-codigo response includes a `Comprador` sub-object with `RegionUnidad`, `ComunaUnidad`, and `DireccionUnidad`
- **THEN** the parsed `LicitacionNotice` exposes those fields through the nested `comprador` attribute
- **AND** the buyer region, commune, and address are accessible and non-null.

#### Scenario: Summary payload has no nested Comprador
- **WHEN** an active-discovery or rolling-window response has flat `CodigoOrganismo`, `NombreOrganismo`, `CodigoUnidad`, `NombreUnidad` at root level and no nested `Comprador`
- **THEN** the parsed `LicitacionNotice` exposes buyer org/unit codes and names through flat fallback fields
- **AND** `comprador` is None
- **AND** buyer region, commune, and address are None (not available in summary).

### Requirement: The parser MUST capture extended Fechas from detail payloads
The system SHALL parse the `Fechas` sub-object into a `FechasPayload` model containing `FechaCreacion`, `FechaCierre`, `FechaInicio`, `FechaFinal`, `FechaPubRespuestas`, `FechaActoAperturaTecnica`, `FechaActoAperturaEconomica`, `FechaPublicacion`, `FechaAdjudicacion`, and `FechaEstimadaAdjudicacion`.

#### Scenario: Detail payload contains nested Fechas
- **WHEN** a detail-by-codigo response includes a `Fechas` sub-object with `FechaCierre` populated
- **THEN** the parsed `LicitacionNotice.close_date` returns the value from `Fechas.FechaCierre`
- **AND** all extended date fields are accessible through the `fechas` attribute.

#### Scenario: Root FechaCierre is null but Fechas.FechaCierre is populated
- **WHEN** a detail-by-codigo response has `"FechaCierre": null` at root but `"Fechas": {"FechaCierre": "2026-05-18T15:10:00"}`
- **THEN** the fallback property `close_date` returns the value from `Fechas.FechaCierre`
- **AND** `close_date` is not None.

### Requirement: The parser MUST capture Items from detail payloads
The system SHALL parse the `Items` sub-object into an `ItemsPayload` model containing a list of `ItemPayload` entries, each with `Correlativo`, `CodigoProducto`, `CodigoCategoria`, `Categoria`, `NombreProducto`, `Descripcion`, `UnidadMedida`, and `Cantidad`.

#### Scenario: Detail payload contains Items with multiple entries
- **WHEN** a detail-by-codigo response includes `Items.Listado` with two items
- **THEN** the parsed `LicitacionNotice.items.listado` contains two `ItemPayload` instances
- **AND** each item has its `CodigoProducto`, `NombreProducto`, `Cantidad`, and `Descripcion` populated.

### Requirement: The parser MUST tolerate mixed types from the API
The system SHALL accept numeric fields as strings, integers, floats, or null without breaking parsing.

#### Scenario: Numeric field comes as string
- **WHEN** the API returns `"DiasCierreLicitacion": "7"` (string) or `"CantidadReclamos": 459` (integer)
- **THEN** the parser converts them to the declared type or preserves them without raising a validation error.

### Requirement: The parser MUST preserve backward compatibility with summary-mode payloads
The system SHALL continue parsing active-discovery and rolling-window summary payloads without errors, producing `LicitacionNotice` instances with only the flat summary fields populated and nested fields as None.

#### Scenario: Active discovery payload is parsed unchanged
- **WHEN** the system runs an active-discovery sync and parses a summary payload
- **THEN** `external_notice_code`, `title`, `official_status_code`, `publication_date`, `close_date`, and flat buyer fields are populated
- **AND** `comprador`, `fechas`, `items`, and `adjudicacion` are None
- **AND** no validation error occurs.

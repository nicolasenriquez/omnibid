# Mercado Publico API Pipeline Hardening Audit

Date: 2026-05-12
Change: `mp-api-pipeline-hardening`

## Scope

Document which fields are in the raw Mercado Publico API detail-by-codigo payload but NOT in the parsed model, NOT in the snapshot table, and NOT in downstream normalized/silver layers.

## Layer 1: Parse Gap (`LicitacionNotice` + `extra="ignore"`)

The current `LicitacionNotice` Pydantic model (`backend/integrations/mercado_publico/schemas.py:38-57`) uses `extra="ignore"` and defines only 12 flat fields. The following detail-by-codigo payload fields are silently discarded at parse time:

| API Field | In `LicitacionNotice`? | Gap |
|---|---|---|
| `Descripcion` (notice-level) | No | Silent discard |
| `Comprador` (nested object) | No | All 12 nested buyer fields dropped |
| `Comprador.RegionUnidad` | No | Buyer region lost |
| `Comprador.ComunaUnidad` | No | Buyer commune lost |
| `Comprador.DireccionUnidad` | No | Buyer address lost |
| `Comprador.RutUnidad` | No | Buyer unit RUT lost |
| `Comprador.RutUsuario` | No | User RUT lost |
| `Comprador.CodigoUsuario` | No | User code lost |
| `Comprador.NombreUsuario` | No | User name lost |
| `Comprador.CargoUsuario` | No | User position lost |
| `Fechas` (nested object) | No | All 10 extended dates dropped |
| `Fechas.FechaCreacion` | No | Creation date lost |
| `Fechas.FechaInicio` | No | Start date lost |
| `Fechas.FechaFinal` | No | End date lost |
| `Fechas.FechaPubRespuestas` | No | Answer publication date lost |
| `Fechas.FechaActoAperturaTecnica` | No | Technical opening date lost |
| `Fechas.FechaActoAperturaEconomica` | No | Economic opening date lost |
| `Fechas.FechaAdjudicacion` | No | Award date lost |
| `Fechas.FechaEstimadaAdjudicacion` | No | Estimated award date lost |
| `Items` (nested object) | No | Entire items list dropped |
| `Items.Listado` (array) | No | Per-item detail dropped |
| `Items.Listado[].Correlativo` | No | Item correlative lost |
| `Items.Listado[].CodigoProducto` | No | ONU product code lost |
| `Items.Listado[].CodigoCategoria` | No | Category code lost |
| `Items.Listado[].Categoria` | No | Category name lost |
| `Items.Listado[].NombreProducto` | No | Product name lost |
| `Items.Listado[].Descripcion` | No | Item description lost |
| `Items.Listado[].UnidadMedida` | No | Unit of measure lost |
| `Items.Listado[].Cantidad` | No | Quantity lost |
| `Adjudicacion` (nested object) | No | All adjudication fields dropped |
| `Adjudicacion.Tipo` | No | Award type lost |
| `Adjudicacion.Fecha` | No | Award date (nested) lost |
| `Adjudicacion.Numero` | No | Award number lost |
| `Adjudicacion.NumeroOferentes` | No | Bidder count lost |
| `Adjudicacion.UrlActa` | No | Award minutes URL lost |
| `Tipo` | No | Procurement type (Publica/Privada) lost |
| `CodigoTipo` | No | Procurement type code (LR/LP/...) lost |
| `TipoConvocatoria` | No | Call type (Abierta/Cerrada) lost |
| `DiasCierreLicitacion` | No | Days to close lost |
| `CantidadReclamos` | No | Claim count lost |
| `FuenteFinanciamiento` | No | Funding source lost |
| `VisibilidadMonto` | No | Visibility budget lost |

Note: Root-level `FechaPublicacion` and `FechaCierre` on the notice are parsed by the existing date validators, but the nested `Fechas.*` extended dates are discarded.

## Layer 2: Snapshot Gap (`mercado_publico_notice_snapshot`)

The current `MercadoPublicoNoticeSnapshot` ORM model (`backend/models/api_source.py:74-123`) mirrors only the 12 flat `LicitacionNotice` fields. No enriched columns exist.

| Column | In snapshot? | Gap |
|---|---|---|
| `description` / `Descripcion` | No | Missing column |
| `buyer_unit_address` / `DireccionUnidad` | No | Missing column |
| `buyer_unit_commune` / `ComunaUnidad` | No | Missing column |
| `buyer_unit_region` / `RegionUnidad` | No | Missing column |
| `buyer_user_rut` / `RutUsuario` | No | Missing column |
| `buyer_user_code` / `CodigoUsuario` | No | Missing column |
| `buyer_user_name` / `NombreUsuario` | No | Missing column |
| `buyer_user_position` / `CargoUsuario` | No | Missing column |
| `created_date` / `FechaCreacion` | No | Missing column |
| `estimated_award_date` / `FechaEstimadaAdjudicacion` | No | Missing column |
| `award_date` / `FechaAdjudicacion` | No | Missing column |
| `tipo` | No | Missing column |
| `codigo_tipo` | No | Missing column |
| `tipo_convocatoria` | No | Missing column |
| `days_to_close` / `DiasCierreLicitacion` | No | Missing column |
| `claim_count` / `CantidadReclamos` | No | Missing column |
| `funding_source` | No | Missing column |
| `visibility_amount` | No | Missing column |
| `api_completeness_level` | No | Missing column (detail vs summary) |
| Items table (`mercado_publico_notice_item_snapshot`) | No | Missing entire table |

## Layer 3: Normalized/Silver Gap

### `normalized_licitaciones`

The `NormalizedLicitacion` model already has columns for:
- `descripcion` — not populated from API snapshots
- `comuna_unidad` — not populated from API snapshots
- `region_unidad` — not populated from API snapshots
- `tipo`, `tipo_convocatoria` — not populated from API snapshots
- `fecha_adjudicacion`, `fecha_estimada_adjudicacion`, `fecha_inicio`, `fecha_final` — not populated from API snapshots
- `cantidad_dias_licitacion` — not populated from API snapshots
- `numero_oferentes` — not populated from API snapshots (available via `Adjudicacion.NumeroOferentes` in detail)
- `visibilidad_monto_raw` — not populated from API snapshots (available via `VisibilidadMonto` in detail)

These columns exist but are NULL for API-sourced rows because the canonicalization layer never receives enriched fields from the snapshot.

### `normalized_licitacion_items`

The `NormalizedLicitacionItem` model exists but has zero rows for API-sourced data because no item persistence exists for API payloads. CSV-source data populates this table, creating a data completeness asymmetry.

### Silver layer

Silver entities (`silver_notice`, `silver_notice_line`, etc.) inherit their NULLs from normalized tables. API-sourced silver notices have:
- `notice_description_raw` = NULL (no `Descripcion` flowing through)
- `notice_description_clean` = NULL
- `notice_line_count` = 0 (no items)
- `number_of_bidders_reported` = NULL
- `complaint_count` = NULL
- `created_date`, `estimated_award_date`, `award_date` = NULL
- No `silver_notice_line` rows for API-sourced notices
- `silver_contracting_unit.unit_address`, `unit_commune`, `unit_region` = NULL for API-sourced units

## Impact Summary

| Layer | Fields lost | Data quality impact |
|---|---|---|
| Parse (`LicitacionNotice`) | ~40 fields silently discarded | Cannot populate snapshot, normalized, or silver with enriched data |
| Snapshot (`mercado_publico_notice_snapshot`) | 18 columns missing + 1 table missing | No persistent record of detail data; items lost entirely |
| Normalized (`normalized_licitaciones`) | 9 columns remain NULL for API sources | UI shows NULL description, region, commune, dates |
| Normalized (`normalized_licitacion_items`) | Zero API-sourced rows | API items invisible in normalized layer |
| Silver (`silver_notice`, `silver_notice_line`, `silver_contracting_unit`) | 7+ columns NULL; no line rows | Silver entities incomplete for all API-sourced notices |

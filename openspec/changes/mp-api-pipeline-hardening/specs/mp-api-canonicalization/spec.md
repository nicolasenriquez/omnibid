# mp-api-canonicalization Specification

## Purpose
Define the contract for mapping enriched API snapshots into the canonical normalized and silver tables, with anti-degradation semantics that prevent NULL overwrites and source priority rules.

## ADDED Requirements

### Requirement: The system MUST map enriched API snapshots to normalized_licitaciones
The system SHALL map fields from enriched `mercado_publico_notice_snapshot` rows into `normalized_licitaciones` columns including `descripcion`, `region_unidad`, `comuna_unidad`, `direccion_unidad`, `tipo`, and extended dates.

#### Scenario: Detail snapshot canonicalizes with all fields
- **WHEN** a snapshot with `api_completeness_level = "detail"` and populated `buyer_unit_region`, `buyer_unit_commune`, `buyer_unit_address`, and `description` is canonicalized
- **THEN** the resulting `normalized_licitaciones` row contains those values in the mapped columns.

#### Scenario: Summary snapshot canonicalizes with partial fields
- **WHEN** a snapshot with `api_completeness_level = "summary"` and NULL enriched fields is canonicalized
- **THEN** the resulting `normalized_licitaciones` row contains only the summary fields that are available
- **AND** enriched columns remain NULL.

### Requirement: The system MUST map API items to normalized_licitacion_items
The system SHALL map rows from `mercado_publico_notice_item_snapshot` into `normalized_licitacion_items` using `external_notice_code` as the parent key.

#### Scenario: Items are canonicalized from item snapshots
- **WHEN** two item snapshot rows exist for `external_notice_code = "1000-8-LE26"`
- **THEN** two rows are inserted or upserted into `normalized_licitacion_items`
- **AND** each row carries `product_code`, `product_name`, `quantity`, `item_description`, and `item_correlative`.

### Requirement: The system MUST NOT overwrite non-null values with NULL
The system SHALL implement anti-degradation semantics: when canonicalizing a new snapshot for an existing normalized entity, non-null values in the target MUST NOT be replaced by NULL values from the source.

#### Scenario: New summary payload does not degrade existing detail data
- **WHEN** a summary-mode snapshot for `CodigoExterno` X is canonicalized after a detail-mode snapshot already populated `descripcion`, `region_unidad`, and `comuna_unidad`
- **THEN** the existing non-null values for `descripcion`, `region_unidad`, and `comuna_unidad` are preserved
- **AND** only fields with actual non-null values in the new snapshot are updated.

#### Scenario: New detail payload updates existing summary data
- **WHEN** a detail-mode snapshot for `CodigoExterno` Y is canonicalized after a summary-mode snapshot has NULL `descripcion`
- **THEN** the `descripcion` is updated to the value from the detail snapshot
- **AND** all other non-null detail fields are populated.

### Requirement: The system MUST follow source priority for conflicting values
The system SHALL apply this priority when merging snapshots: detail-by-codigo > rolling-window > active-discovery.

#### Scenario: Detail payload takes priority over summary payload
- **WHEN** a detail-mode snapshot and a summary-mode snapshot both have a value for `MontoEstimado` but differ
- **THEN** the detail-mode value is used in the canonical entity
- **AND** the summary-mode value is discarded for that field.

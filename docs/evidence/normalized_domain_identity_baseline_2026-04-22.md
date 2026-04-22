# Normalized Domain Identity Baseline (Controlled Samples)

Date: 2026-04-22  
Change: `expand-normalized-domain-buyers-suppliers-categories`

## Objective

Establish pre-implementation baseline for buyer/supplier/category identity coverage and confirm deterministic business-key precedence for domain canonicalization.

## Controlled Datasets

- `../dataset-mercado-publico/licitacion/202601_lic.csv`
- `../dataset-mercado-publico/orden-compra/202604-oc.csv`

CSV parse assumptions:
- encoding: `latin1`
- delimiter: `;`
- empty-like tokens treated as missing: `""`, `NA`, `N/A`, `NULL`

## Identity Coverage Results

### Licitacion (`202601_lic.csv`)

- total rows: `116,658`
- `CodigoProveedor`: `116,658 / 116,658` (`100.00%`)
- `RutProveedor`: `116,658 / 116,658` (`100.00%`)
- supplier identity (`CodigoProveedor` OR `RutProveedor`): `116,658 / 116,658` (`100.00%`)
- `CodigoUnidadCompra`: column not present
- `codigoCategoria`: column not present

### Orden Compra (`202604-oc.csv`)

- total rows: `208,252`
- `CodigoUnidadCompra`: `208,252 / 208,252` (`100.00%`)
- `CodigoProveedor`: `208,252 / 208,252` (`100.00%`)
- supplier identity (`CodigoProveedor` OR `RutProveedor`): `208,252 / 208,252` (`100.00%`)
- `codigoCategoria`: `173,101 / 208,252` (`83.12%`)
- `RutProveedor`: column not present

## Deterministic Business-Key Contract Confirmation

Confirmed and aligned with OpenSpec scenarios:

1. Buyer identity:
- key source: `CodigoUnidadCompra`
- canonical key format: raw key value as-is
- fail-fast/rejection rule: if missing/empty, no buyer domain write; persist quality issue

2. Supplier identity:
- precedence: `CodigoProveedor` first, fallback `RutProveedor`
- canonical key format: `codigo:<value>` or `rut:<value>`
- fail-fast/rejection rule: if both missing/empty, no supplier domain write; persist quality issue

3. Category identity:
- key source: `codigoCategoria`
- canonical key format: raw key value as-is
- fail-fast/rejection rule: if missing/empty, no category domain write; persist quality issue

## Stage-1 Gate Outcome

- Task `1.1`: PASS (coverage baseline captured)
- Task `1.2`: PASS (key-precedence and rejection contract confirmed)
- Stage status: GREEN; Stage 2 (TDD) is unlocked.

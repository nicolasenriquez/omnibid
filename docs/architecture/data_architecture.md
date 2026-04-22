# Data Architecture

## Raw
Raw data + lineage + source metadata.

## Normalized
Clean relational entities:
- licitaciones
- licitacion_items
- ofertas
- ordenes_compra
- ordenes_compra_items
- buyers (canonical domain)
- suppliers (canonical domain)
- categories (canonical domain)

Canonical domain identity contracts:
- buyer key: `buyer_key` (`CodigoUnidadCompra`)
- supplier key: `supplier_key` with typed precedence `codigo:<CodigoProveedor>` then `rut:<RutProveedor>`
- category key: `category_key` (`codigoCategoria`)

Transactional normalized tables retain descriptive fields for compatibility, and now
also include nullable relational key columns (`buyer_key`, `supplier_key`, `category_key`)
to support explicit joins to canonical domain entities.

## Gold (minimal)
Business-ready summaries:
- buyer profile
- supplier profile
- periodic summaries

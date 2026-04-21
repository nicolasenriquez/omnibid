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

Buyer/supplier attributes currently live inside `normalized_ordenes_compra` and
`normalized_ofertas`. Dedicated buyer/supplier tables are a future extension, not
part of the current physical schema.

## Gold (minimal)
Business-ready summaries:
- buyer profile
- supplier profile
- periodic summaries

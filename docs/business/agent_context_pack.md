# Agent Context Pack

## Purpose
Provide a compact working summary for future agents before they touch code or docs.

## 10-line summary
1. `omnibid` is a deterministic procurement intelligence platform.
2. The main business is supplier-side opportunity discovery and bid support.
3. ChileCompra's Mercado Publico is the operational source of public procurement activity.
4. Datos Abiertos is the historical batch source.
5. The API is the operational refresh source.
6. Raw keeps lineage.
7. Normalized keeps canonical query-ready entities.
8. Silver keeps deterministic procurement-cycle facts and annotations.
9. Gold is reserved for aggregates, scoring, prediction, and recommendations.
10. Human review remains mandatory for bidding and compliance decisions.

## 12-step procurement flow
1. notice publication
2. read bases
3. check eligibility
4. open forum
5. publish answers
6. prepare offer
7. close
8. technical opening
9. economic opening
10. evaluation
11. adjudication
12. purchase order, acceptance, reception, execution

## Official sources
- Mercado Publico
- ChileCompra
- Datos Abiertos
- API de Mercado Publico
- Registro de Proveedores
- Compra Agil
- Convenio Marco
- Trato Directo
- Ley 19.886
- Ley 21.634
- Decreto 661/2024
- BCN LeyChile

## Main entities
- notice
- notice line
- bid submission
- award outcome
- purchase order
- purchase order line
- buying org
- contracting unit
- supplier
- category

## Current repo tables
- `normalized_licitaciones`
- `normalized_licitacion_items`
- `normalized_ofertas`
- `normalized_ordenes_compra`
- `normalized_ordenes_compra_items`
- `normalized_buyers`
- `normalized_suppliers`
- `normalized_categories`
- `silver_notice`
- `silver_notice_line`
- `silver_bid_submission`
- `silver_award_outcome`
- `silver_purchase_order`
- `silver_purchase_order_line`
- `silver_buying_org`
- `silver_contracting_unit`
- `silver_supplier`
- `silver_category_ref`
- `silver_notice_purchase_order_link`
- `silver_supplier_participation`
- `silver_notice_text_ann`
- `silver_notice_line_text_ann`
- `silver_purchase_order_line_text_ann`

## Layer boundaries
- Raw: traceability and source metadata.
- Normalized: canonical, query-ready domain tables.
- Silver: deterministic facts and technical annotations.
- Gold: aggregates, scores, predictions, and recommendations.

## No-invention rules
- Do not invent headers, states, or date semantics.
- Do not assume every OC links to a notice.
- Do not assume every notice ends in an OC.
- Do not treat ONU-only matching as conclusive.
- Do not persist agent narrative as canonical fact.

## Before touching code
- Confirm the source contract in docs.
- Confirm the table grain.
- Confirm optional links are optional.
- Confirm the change belongs in the right layer.

## Before touching docs
- Reuse the current domain language.
- Separate official facts from observations.
- Note any open question explicitly.

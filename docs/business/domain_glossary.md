# Domain Glossary

## Purpose
Normalize the procurement language used by humans, official sources, and the repo tables.

## Audience
- analysts
- product and engineering agents

## Glossary

| Término oficial | Nombre canónico interno | Definición | Fuente oficial | Campos relacionados | Tablas actuales relacionadas | Notas de modelamiento | Ambigüedades / validation tasks |
|---|---|---|---|---|---|---|---|
| Mercado Publico | `market_public` | Transactive platform for public procurement. | ChileCompra / Mercado Publico | portal, notices, OCs, suppliers | `source_files`, `raw_*`, `normalized_*`, `silver_*` | Use as platform label, not entity grain. | Distinguish platform from notice or order. |
| ChileCompra | `chilecompra` | Public agency that administers the system. | chilecompra.cl | rules, APIs, open data | docs only | Not a persisted business table. | Keep institution separate from platform. |
| Datos Abiertos | `open_data_batch` | Public historical data downloads and OCDS access. | Datos Abiertos site | CSV, JSON, OCDS | `raw_*`, `normalized_*` | Batch source, not live state. | Validate headers per dataset/month. |
| Licitacion publica | `notice` | Open procurement procedure. | Mercado Publico help pages | `CodigoExterno`, dates, state | `normalized_licitaciones`, `silver_notice` | Parent grain for opportunity work. | Public or private? verify `TipoConvocatoria`. |
| Licitacion privada | `private_notice` | Invitation limited to selected providers. | Mercado Publico help pages | type, invitation scope | `normalized_licitaciones`, `silver_notice` | Keep as a distinct procurement mode. | Confirm representation in current sources. |
| Bases de licitacion | `notice_bases` | Requirements, conditions, specs, and criteria. | Mercado Publico help pages | attachments, description, dates | source docs, `source_files` | Often lives outside structured rows. | Need attachment review and OCR extraction. |
| Oferta | `bid_submission` | Provider proposal against a notice. | Mercado Publico help pages | offer name, selected flag, amount | `normalized_ofertas`, `silver_bid_submission` | May exist at line and supplier grain. | Validate rejected vs selected offers. |
| Oferente | `bidder` | Entity that submits an offer. | Mercado Publico help pages | supplier identifiers | `normalized_suppliers`, `silver_supplier` | Human role, not always equal to supplier master. | Same company can appear in multiple roles. |
| Proveedor | `supplier` | Party that sells to the State. | Registro de Proveedores / Mercado Publico | supplier codes, RUT, name | `normalized_suppliers`, `silver_supplier` | Use supplier master as canonical identity. | Multiple codes or branches may exist. |
| Registro de Proveedores | `supplier_registry` | Eligibility registry managed by ChileCompra. | ChileCompra registry page | habilitado, inhabilidades | `normalized_suppliers`, `silver_supplier` | Separate eligibility from commercial participation. | Treat registry status as a fact with time. |
| Foro de preguntas | `question_forum` | Q&A channel on a notice. | Mercado Publico help pages | start/end forum dates | not yet canonical | Important for deadline and scope changes. | May require docs or attachments. |
| Publicacion de respuestas | `answers_publication` | Release of forum answers. | API / help pages | `Fechas/FechaPubRespuestas` | `silver_notice` | Useful alert point. | Validate if answers alter bases. |
| Apertura tecnica | `technical_opening` | Technical bid opening event. | API licitaciones | `Fechas/FechaActoAperturaTecnica` | `silver_notice` | A key milestone for alerts. | May be delayed or rescheduled. |
| Apertura economica | `economic_opening` | Economic bid opening event. | API licitaciones | `Fechas/FechaActoAperturaEconomica` | `silver_notice` | Often follows technical opening. | Needs document review. |
| Evaluacion | `evaluation` | Review of bids and evidence. | API licitaciones | `Fechas/FechaTiempoEvaluacion`, reclamos | `silver_notice` | Not a score, only a process stage. | Keep deterministic and human-auditable. |
| Adjudicacion | `award` | Selection of the winning offer. | API / help pages | award dates, decision text | `silver_award_outcome` | Canonical award evidence. | Do not infer from price alone. |
| Acta de adjudicacion | `award_act` | Formal award record. | help pages / attachments | acta, resolution, date | source docs | Strong evidence of award. | May be attached as PDF. |
| Orden de compra | `purchase_order` | Electronic order sent to supplier. | Mercado Publico / API | `Codigo`, `FechaEnvio`, status | `normalized_ordenes_compra`, `silver_purchase_order` | Optional link to a notice. | `CodigoLicitacion` can be empty. |
| Recepcion conforme | `receipt_accepted` | Accepted delivery/receipt status. | API OC states | `Estado`, `EstadoProveedor` | `silver_purchase_order` | Part of execution, not award. | Multiple receipt states exist. |
| Organismo comprador | `buying_org` | Public entity that buys. | ChileCompra / API | buyer org code, name | `normalized_buyers`, `silver_buying_org` | Buyer master entity. | Distinguish org from contracting unit. |
| Unidad de compra | `contracting_unit` | Buyer unit that runs the process. | API licitaciones / OC | unit code, name, address | `normalized_buyers`, `silver_contracting_unit` | Operational unit inside the buyer org. | May differ from org-level reporting. |
| Item / linea | `line_item` | Notice or OC line. | CSV / API fields | item codes, quantities, amounts | `normalized_licitacion_items`, `normalized_ordenes_compra_items`, `silver_notice_line`, `silver_purchase_order_line` | Use line-grain evidence explicitly. | Notice and OC lines are not the same grain. |
| Codigo ONU / UNSPSC | `onu_product_code` | Product/category code used to classify goods. | ChileCompra / API / CSV | product code, category | `normalized_categories`, `silver_category_ref` | Useful for approximate evidence only. | ONU-only matching is plausible, not conclusive. |
| Compra Agil | `quick_purchase` | Special fast purchasing procedure. | ChileCompra help pages | `Estado`, OC, amount | may appear in source rows | Separate channel, not standard licitation. | Validate the 100 UTM rule per source. |
| Convenio Marco | `framework_agreement` | Competitive framework that feeds a catalog. | ChileCompra help pages | CM code, catalog refs | source docs, normalized docs | Catalog-driven procurement path. | Not every opportunity is a classic notice. |
| Trato Directo | `direct_contracting` | Exceptional direct contracting with publicity. | ChileCompra help pages | resolution, intention, OC | source docs, normalized docs | Keep as a distinct procurement mode. | Not the same as open tendering. |
| OCDS | `ocds_record` | Open Contracting Data Standard. | Datos Abiertos / ChileCompra | structured contract data | source docs / future ingestion | Format and publication standard. | Need to distinguish from local CSV shape. |

## Validation checklist
- Keep source terms and internal names separate.
- If a term is not yet modeled, say so.
- Use this glossary to align docs before code.

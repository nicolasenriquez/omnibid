# Market Public Domain Overview

## Purpose
Explain the procurement domain that `omnibid` works against, using official ChileCompra and Mercado Publico sources.

## Audience
- humans who need a fast domain refresher
- agents that must understand the business before touching code

## Scope
This document separates official definitions from the interpretation used by `omnibid`.

## Official sources
- [Mercado Publico](https://www.chilecompra.cl/mercado-publico/)
- [Que es una licitacion](https://www.mercadopublico.cl/Home/Contenidos/QueEsLicitacion)
- [Que es Mercado Publico](https://www.mercadopublico.cl/Home/Contenidos/QueesMercadoPublico)
- [Como vender al Estado](https://www.chilecompra.cl/como-vender-al-estado/)
- [Compra Agil FAQ](https://ayuda.mercadopublico.cl/preguntasfrecuentes/article/KA-01979/es-es)
- [Convenio Marco FAQ](https://ayuda.mercadopublico.cl/preguntasfrecuentes/article/KA-01956/es-es)
- [Trato Directo FAQ](https://ayuda.mercadopublico.cl/preguntasfrecuentes/article/KA-01942/es-es)

## Definitions

| Term | Official meaning | Business meaning | Data implication |
|---|---|---|---|
| Mercado Publico | ChileCompra's transactive platform for public procurement. | Main surface where opportunities, orders, and supplier activity appear. | Source for operational queries and public-facing status. |
| ChileCompra | Public agency that administers the system. | The institutional owner of the procurement rules and platform. | Official source of rules, APIs, and open data. |
| Datos Abiertos | Public, reusable procurement data, including OCDS. | Historical and analytical backbone. | Better for batch ingestion, exploration, and lineage. |
| Licitacion publica | Open procurement procedure where any qualified provider can submit offers. | The main opportunity type for our supplier-side workflow. | Model as a notice with lines, offers, awards, and possible OC links. |
| Licitacion privada | Invitation-based procurement procedure limited to selected providers. | A narrower opportunity path with controlled participation. | Model separately from open public tenders. |
| Bases de licitacion | Requirements, conditions, specs, evaluation criteria, and guarantees. | The document humans must read before bidding. | Often requires attached documents, not just structured fields. |
| Oferta | Provider response to a notice. | The candidate proposal we compare and prepare. | May exist at line, supplier, and award grain. |
| Adjudicacion | Selection of the most convenient offer. | Key milestone before contract or OC follow-up. | Often only visible after evaluation and award dates. |
| Orden de compra | Electronic purchase order emitted by the buyer. | The operational follow-through after award or other purchase modes. | Can link back to a notice, but the link is optional. |
| Registro de Proveedores | Eligibility registry managed by ChileCompra. | Gate for who can legally participate and sign. | Supplier eligibility should be treated as a separate fact. |
| Compra Agil | Fast purchasing procedure for smaller amounts, prioritizing EMTs. | A separate opportunity channel with different rules. | Not the same as a classic licitacion. |
| Convenio Marco | Competitive procedure that feeds a catalog for recurring purchases. | A preferred channel for standardized goods and services. | Needs separate handling because the grain is catalog-driven. |
| Trato Directo | Exceptional direct contracting with regulated causes and publicity. | A non-open fallback path that still needs tracking. | Not interchangeable with open bidding data. |

## Data implications
- The domain is hierarchical, not flat.
- A notice can have lines, offers, awards, and purchase orders.
- Some purchase orders are not tied to a notice.
- Some procurement modes are not classic public tenders.

## Product implications
- `omnibid` should help teams find opportunities, understand them, and decide whether to bid.
- The app should support supplier-side work, not replace public buyer workflows.
- The app should keep humans in the loop for legal, commercial, and compliance decisions.

## Risks
- Treating all procurement modes as the same entity.
- Assuming a purchase order always comes from a notice.
- Assuming the CSV and API have the same grain.

## Validation checklist
- Confirm source URLs stay in the registry.
- Keep business language distinct from table names.
- Mark anything uncertain as an observation.

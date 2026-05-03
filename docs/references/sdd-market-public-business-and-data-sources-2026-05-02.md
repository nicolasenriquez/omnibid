# SDD Reference Note

## Metadata

- Change/Proposal: Business documentation for Mercado Publico and source contracts
- Date: 2026-05-02
- Author: Codex
- Area: docs

## Question

- How should `omnibid` document the Mercado Publico domain so future agents do not confuse historical CSV downloads with the operational API?

## Official Sources Consulted

1. https://www.chilecompra.cl/mercado-publico/
   - Topic: Mercado Publico overview
   - Relevant contract: platform definition and public view
2. https://www.mercadopublico.cl/Home/Contenidos/QueEsLicitacion
   - Topic: licitacion definition and bases
   - Relevant contract: open and private tenders
3. https://www.chilecompra.cl/api/
   - Topic: API overview and usage
   - Relevant contract: operational access, ticketing, query styles
4. https://www.chilecompra.cl/wp-content/uploads/2026/03/Documentacion-API-Mercado-Publico-Licitaciones.pdf
   - Topic: licitacion API dictionary
   - Relevant contract: state codes, field names, GET parameters
5. https://www.chilecompra.cl/wp-content/uploads/2026/03/Documentacion-API-Mercado-Publico-oc.pdf
   - Topic: OC API dictionary
   - Relevant contract: OC states, fields, GET parameters
6. https://www.chilecompra.cl/datos-abiertos/
   - Topic: open data purpose
   - Relevant contract: historical, reusable, OCDS-aligned data
7. https://datos-abiertos.chilecompra.cl/
   - Topic: download surface
   - Relevant contract: JS-rendered downloads and dataset evidence
8. https://www.chilecompra.cl/registro-de-proveedores/
   - Topic: supplier registry
   - Relevant contract: eligibility and habilitation
9. https://ayuda.mercadopublico.cl/preguntasfrecuentes/article/KA-01979/es-es
   - Topic: Compra Agil
   - Relevant contract: fast purchasing procedure
10. https://ayuda.mercadopublico.cl/preguntasfrecuentes/article/KA-01956/es-es
   - Topic: Convenio Marco
   - Relevant contract: catalog-driven procurement
11. https://ayuda.mercadopublico.cl/preguntasfrecuentes/article/KA-01942/es-es
   - Topic: Trato Directo
   - Relevant contract: exceptional direct contracting and publicity
12. https://www.chilecompra.cl/ley-de-compras-publicas/
   - Topic: law modernization
   - Relevant contract: Ley 19.886 and Ley 21.634 context
13. https://www.chilecompra.cl/terminos-y-condiciones-de-uso/
   - Topic: system conditions
   - Relevant contract: system scope and public data rules
14. https://www.bcn.cl/leychile/navegar?idNorma=213004&idVersion=2024-12-12
   - Topic: Ley 19.886 official text
   - Relevant contract: normative basis and publication requirements
15. https://www.bcn.cl/leychile/navegar?idNorma=1198903
   - Topic: Ley 21.634 official text
   - Relevant contract: modernization and circular-economy changes
16. https://www.bcn.cl/leychile/navegar?i=1209290
   - Topic: Decreto 661/2024 official text
   - Relevant contract: current procurement regulation

## Decision

- What was implemented: a new `docs/business/` folder, a compact agent context pack, separate CSV and API contracts, a glossary, a lifecycle map, and a domain overview.
- Why this matches official source: ChileCompra documents treat Mercado Publico, Datos Abiertos, and the API as related but distinct surfaces, with different purposes and usage patterns.

## Code Impact

- Files touched: new `docs/business/*.md`, `docs/README.md`, `docs/references/sdd-official-sources-registry.md`
- Behavioral impact: none in runtime code; future agents now have a clearer business and source contract

## Validation

- Tests/checks executed: documentation-only source review and repo doc alignment
- Result: no pipeline or runtime validation was needed for this docs-only change

## Notes / Risks

- Open questions: which CSV variants should be promoted to canonical evidence first, and whether some procurement modes need dedicated raw datasets.
- Follow-up actions: capture real CSV headers in `docs/evidence/` when a validation run is requested.

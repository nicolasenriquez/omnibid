# Business Documentation

## Purpose
This folder explains the procurement domain, business lifecycle, and source contracts that matter for `omnibid`.
It is written for both humans and agents, but it is not legal advice and does not replace the official ChileCompra texts.

## Audience
- product and engineering agents
- analysts and operators
- future maintainers

## Relationship to other docs
- `docs/architecture/` describes canonical layers and tables.
- `docs/references/` stores official sources and SDD notes.
- `docs/evidence/` stores validation artifacts and observed headers.
- `docs/product/` captures product direction and scope.

## Recommended read order
1. `docs/README.md`
2. `docs/architecture/data_architecture.md`
3. `docs/architecture/data_model.md`
4. `docs/business/agent_context_pack.md`
5. `docs/business/market_public_domain_overview.md`
6. `docs/business/procurement_lifecycle.md`
7. `docs/business/data_sources_downloads_vs_api.md`
8. `docs/business/downloaded_csv_contracts.md`
9. `docs/business/api_contracts_market_public.md`
10. `docs/business/domain_glossary.md`
11. `docs/business/intermediary_business_model.md`
12. `docs/business/opportunity_analysis_framework.md`

## Boundary
This folder captures business meaning, observed source behavior, and product implications.
Technical contracts still live in architecture docs, models, migrations, tests, and evidence.
When a statement is uncertain, label it as an observation or open question instead of turning it into a fact.

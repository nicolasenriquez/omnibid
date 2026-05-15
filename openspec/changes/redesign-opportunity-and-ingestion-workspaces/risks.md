## Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Inventing data from the mockups | The screenshots are directional, not contractual. | Keep the audit authoritative and mark every unsupported field as unavailable. |
| Overloading the opportunity workspace | A dashboard-heavy shell can hide the actual triage flow. | Keep `/licitaciones` focused on review and move diagnostics to `Ingestion Center`. |
| Mixing read-only and mutable semantics | Users can assume actions persist when they do not. | Keep copy explicit: local-only watchlist, no fake write actions, no implied authority. |
| Leaking predictive language into Silver | A score, rank, or recommendation can be mistaken for ground truth. | Keep `*_score`, `*_probability`, `forecast_*`, and `recommendation_*` out of Silver and out of v1. |
| Slow queries on large fact sets | The review flow will feel broken if counts and snapshots are slow on `silver_notice` (~122k), `silver_bid_submission` (~2.1M), `silver_purchase_order` (~2.4M). | Use existing summary endpoints first; add read models or materialized views only where the audit justifies them. |
| Contract drift across surfaces | The same fact can look different in the workspace and the ingestion center. | Reuse a shared UI system and one explicit availability model. |
| UI coupling to incomplete document data | Docs/bases/anexos are easy to imply but hard to source. | Keep them out of scope until a real document path exists. |
| Breaking existing contracts during transition | Adding new views while deprecating old ones can break deep links or URL state. | Keep `Explorador`/`Radar` coexisting with `Lista`/`Tabla` until parity; gate new views behind toggles if needed. |
| Introducing scoring without Gold layer | Priorización labels can drift into score-like semantics over time. | Use deterministic bucket labels only; never expose numeric scores or rankings. Audit each bucket's rule provenance before shipping. |

## Decisions Resolved

- **Ingestion Center route**: Dedicated route (`/ingesta`). Keeps operational UI separate from commercial triage.
- **Priorización scope**: Urgency buckets only in v1 ("Revisar hoy", "Cierra esta semana", "Abierta con plazo", "En radar"). Fit buckets deferred to `opportunity-workspace-decision-first-upgrade`.
- **Buyer history snapshot**: Derived backend from existing Silver facts in Phase 4. Rendered as `Sin historial suficiente` when data is sparse.
- **Documents/bases/anexos**: Require a new document registry and ingestion path. Rendered as `Sin dato — requiere registro documental futuro` in v1.
- **API diagnostics**: Summary metrics first (counts, status aggregates). Direct request-ledger deferred to Phase 6+.


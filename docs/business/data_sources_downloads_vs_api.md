# Data Sources: Downloads vs API

## Purpose
Explain why `omnibid` should treat Datos Abiertos CSV downloads and the Mercado Publico API as different contracts.

## Audience
- engineers building ingestion and read paths
- analysts deciding which source to trust for each use case

## Key takeaway
> CSV mensual = historical / batch / EDA / contextual training / mass analysis.
> API = operational query / active tenders / detail by code / incremental integration.

## Official sources
- [Datos Abiertos](https://www.chilecompra.cl/datos-abiertos/)
- [Datos Abiertos site](https://datos-abiertos.chilecompra.cl/)
- [API de Mercado Publico](https://www.chilecompra.cl/api/)
- [API Licitaciones PDF](https://www.chilecompra.cl/wp-content/uploads/2026/03/Documentacion-API-Mercado-Publico-Licitaciones.pdf)
- [API OC PDF](https://www.chilecompra.cl/wp-content/uploads/2026/03/Documentacion-API-Mercado-Publico-oc.pdf)

## Comparison

| Dimension | Datos Abiertos CSV mensual | Mercado Publico API |
|---|---|---|
| Purpose | Historical and analytical archive. | Operational access to current public data. |
| Grain | Monthly download, may mix multiple business grains. | Object-centric query contract by code, date, state, org, or supplier. |
| Frequency | Batch by month, with dataset-specific drift risk. | On-demand and incremental. |
| Format | CSV, often with variable headers. | JSON, JSONP, and XML. |
| Access | Download from the open-data site. | GET requests with a ticket. |
| Strengths | Great for history, EDA, and broad joins. | Great for active monitoring, alerts, and detail lookup. |
| Weaknesses | Not ideal for real-time operational checks. | Not ideal as the only historical warehouse source. |
| Schema drift | High risk, especially across months and years. | Lower at the envelope level, but legacy field names still exist. |

## When to use each source
- Use CSV downloads for Raw ingestion, Normalized history, Silver canonical history, and exploratory analysis.
- Use the API for active opportunity refresh, point lookups by code, and incremental enrichment.
- Do not assume the API and CSV share the same grain or the same headers.

## How to combine them in `omnibid`
- Persist CSVs as traceable raw batches.
- Normalize source-specific headers into canonical tables.
- Use API lookups to enrich open notices or verify recent state changes.
- Keep optional links optional, especially for purchase orders without a notice reference.
- Document every observed mismatch in `docs/evidence/`.

## Validation and drift controls
- Verify headers against a real CSV file before mapping.
- Record encoding, delimiter, quoting, and null conventions.
- Compare CSV headers to API field names, but do not force them to match.
- Treat a new or missing column as a drift event, not as a silent fallback.

## Risks
- A CSV row can represent more than one business grain.
- A purchase order row can be line-level rather than header-level.
- A notice can exist without a later purchase order.
- A purchase order can exist without a linked notice.

## Validation checklist
- Keep CSV and API contracts separate in docs and code.
- Use the API for live state, not for batch history.
- Use CSV for history, not as a proxy for live opportunity state.

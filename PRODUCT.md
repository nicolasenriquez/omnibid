# Product

## Register

product

## Users

Procurement analysts and managers form the primary user layer. They browse, filter, and analyze ChileCompra public procurement opportunities (licitaciones) across stages, with support for watchlists, KPI snapshots, and exports. Data engineers constitute a secondary layer that reviews ingestion pipelines and manual CSV upload flows.

## Product Purpose

Omnibid provides a deterministic procurement data workspace. Users search and filter licitaciones by stage, close date, amount, buyer, and category; pivot between radar (kanban) and explorer (table) views; and drill into individual opportunity detail with line/offer/purchase-order evidence. The pipeline layer ingests Mercado Público datasets and manual CSV uploads into a traceable raw-to-normalized data foundation.

## Brand Personality

**Confident, modern, focused.** The interface should feel sharp and opinionated like a professional tool (Linear, Stripe energy) — every pixel serves the task. No decoration, no hesitation. The visual language earns trust through precision and restraint.

## Anti-references

- **Generic enterprise dashboards**: Avoid Material Design defaults, heavy fixed sidebars, oversized hero sections, boring unstyled tables, cluttered form layouts.
- **Legacy government portals**: Avoid dated table styling, poor contrast, slow page loads, information overload.
- **Flashy marketing surfaces**: No gradient text, glassmorphism defaults, hero metrics, excessive decorative animation.

## Design Principles

1. **Data-first clarity**: Tables, metrics, and filters are the hero — chrome recedes.
2. **Earned familiarity**: Use standard patterns users know (tabs, tables, search, filter chips). Consistency across views is an affordance.
3. **Quiet confidence**: Surfaces feel deliberate and composed. Accent color is reserved for action and selection, not decoration.
4. **Depth without noise**: Dense information (KPIs, evidence panels, upload console) stays readable through careful typography, spacing, and surface layering.

## Accessibility & Inclusion

- WCAG 2.1 AA compliance target.
- Semantic HTML, ARIA labels on interactive regions, screen-reader live regions.
- Keyboard navigation for the full workspace (Escape closes detail, sort controls, watchlist toggle).
- Respect `prefers-reduced-motion` for transitions and loading animations.

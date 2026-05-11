# Component Standards

## Purpose

Shared UI components should act as stable primitives. They should not encode page-specific styling decisions.

## Shared Primitives

- `Button`
- `IconButton`
- `Input`
- `Select`
- `Badge`
- `Chip`
- `Card`
- `Panel`
- `Skeleton`
- `Table`
- `TableWrap`
- `Tabs`
- `DetailSection`

## Rules

- Reuse the shared primitive before adding a new one.
- Keep `Card` and `Panel` visually compatible.
- Use `Card` for route shells and general surfaces when the design calls for a card-like container.
- Keep state variants explicit:
  - default
  - hover
  - active
  - focus-visible
  - disabled
  - loading
  - error
  - selected
- Use one icon library consistently. The current standard is `lucide-react`.
- Prefer tokens and shared component classes over inline styles.

## Route States

- Loading, empty, error, and not-found screens should be built from the same component boundaries as the rest of the app.
- Keep their copy concise and in Spanish when they are part of the procurement workspace.

## Accessibility

- Preserve keyboard focus visibility.
- Preserve semantic HTML first, styling second.
- Do not use color alone to communicate state.

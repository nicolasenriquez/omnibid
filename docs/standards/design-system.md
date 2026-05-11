# Design System Standard

## Purpose

This repository uses a CSS-first design system for the `client/` app. The system is intentionally small and is meant to keep the workspace consistent without adding a separate styling framework.

The detailed standards are split into:

- [`design-tokens.md`](design-tokens.md)
- [`component-standards.md`](component-standards.md)
- [`motion-standards.md`](motion-standards.md)

## Files Of Record

- `client/src/styles/tokens.css` for semantic design tokens.
- `client/src/styles/workspace.css` for workspace-specific layout and component styles.
- `client/src/components/ui/` for shared UI primitives.
- `client/app/licitaciones/` for route-state surfaces such as loading, empty, 404, and error views.
- `client/src/features/opportunity-workspace/display-contract.ts` for Spanish labels and read-only action text.

## Token Rules

- Use semantic tokens instead of raw values in components and page shells.
- Prefer `--color-*`, `--space-*`, `--font-*`, and `--motion-*` tokens.
- Keep spacing on a 4px base.
- Keep typography on a shared scale instead of inventing page-specific text sizes.
- Add motion tokens for transitions instead of scattering hardcoded durations.
- If a pattern is reused, give it a stable semantic token name instead of a page-specific literal.

## Component Rules

- Use the shared primitives before creating new one-off UI surfaces.
- `Button`, `Input`, `Badge`, `Card`, `Panel`, `Select`, `Table`, and `Tabs` are the shared UI boundary.
- Keep `Panel` compatible with `Card` so existing code does not need a full rename.
- Use the same component for the same visual role across screens.
- Support the relevant states explicitly: default, hover, active, focus-visible, disabled, loading, error, and selected.

## Route States

- Route-level loading, error, and not-found views should use the shared card surface and token-driven spacing.
- Do not use inline hex colors or inline padding for those screens.
- Keep the message text concise and in Spanish.

## Icon And Motion

- Standardize on `lucide-react` for icons.
- Keep motion purposeful and short.
- Prefer transitions under 300ms unless there is a clear interaction reason to go longer.
- Respect reduced-motion preferences.

## Procurement Workspace Rules

- Keep list and detail styling aligned to the same token system.
- Keep business labels in `display-contract.ts`.
- Do not move product-language strings into CSS.
- Avoid hardcoded colors in React components.
- Use status tokens for procurement states rather than inventing ad hoc colors.

## Future Dark Mode

- Dark mode, if added later, should be implemented by swapping token values, not by rewriting components.
- Avoid introducing new light-only assumptions into shared primitives.

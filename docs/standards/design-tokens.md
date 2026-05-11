# Design Tokens Standard

## Purpose

Design tokens are the single source of truth for the client UI. Use them to keep visual decisions semantic, repeatable, and easy to change.

## Rules

- Use semantic tokens in components and page shells instead of raw values.
- Prefer the existing token groups:
  - `--color-*` for semantic colors.
  - `--space-*` for spacing.
  - `--font-*` for typography.
  - `--radius-*` for corner treatment.
  - `--shadow-*` for elevation.
  - `--motion-*` for interaction timing.
- Keep spacing on a 4px base.
- Keep typography on the shared scale already defined in `tokens.css`.
- Add new tokens only when a repeated pattern needs a stable semantic name.
- Do not create screen-specific tokens unless the pattern is reused.

## Domain Tokens

The procurement workspace may define business-language aliases on top of the core palette.

- Tender states should map to semantic status tokens.
- Upload and console states should map to shared status, surface, and motion tokens.
- Route states should use shared shell tokens rather than inline colors.

## Tailwind Bridge

If Tailwind utilities are used, map them to the same token names in `client/tailwind.config.ts`.
That keeps utility classes and CSS modules aligned instead of creating two parallel design systems.

## Context

The raw pipeline is already in place. The next risk is normalized-layer correctness and reliability when loading wide CSV datasets with mixed types and repeated header fields at item grain.

## Design Goals

- Keep business-key upsert semantics explicit and deterministic.
- Enforce stronger input normalization and required-field checks.
- Preserve current functionality while reducing silent data quality drift.
- Keep implementation localized to normalized-layer loaders/transforms and their tests.

## Technical Approach

1. Strengthen transform helpers (`parse_*`, `pick`, flags) with additional edge-case handling and explicit null/sentinel normalization.
2. Harden upsert flow in `build_normalized.py` with clear conflict keys and rejection accounting.
3. Add focused tests for:
   - licitaciones header/item/oferta mapping
   - ordenes_compra header/item mapping
   - numeric/date/boolean coercion edge cases
4. Keep migration scope minimal in this change unless hard schema issues are discovered.

## Risks

- Schema drift across monthly source files can break assumptions.
- Large batches can mask partial failures if metrics are weak.
- Over-normalization could unintentionally alter business semantics.

## Mitigations

- Fail-fast on missing required fields for critical keys.
- Add explicit row-level rejection counters and logs.
- Expand unit tests before refactors.

## Open Questions

None.

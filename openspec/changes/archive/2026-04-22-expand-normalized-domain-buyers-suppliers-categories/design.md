## Context

The repository completed the reliability hardening sequence and stabilized normalized ingestion behavior. The next stage gate requires canonical domain modeling before starting Gold outputs.

Today, buyer, supplier, and category attributes are duplicated inside transactional normalized tables (`normalized_ordenes_compra`, `normalized_ofertas`, `normalized_ordenes_compra_items`) rather than represented as dedicated domain entities. This makes joins, consistency checks, and downstream semantics harder to manage.

## Goals / Non-Goals

**Goals:**
- Introduce canonical normalized domain entities for buyers, suppliers, and categories.
- Define deterministic business-key contracts and idempotent upsert semantics for each domain entity.
- Populate domain entities from existing normalized transactional sources in a deterministic sequence.
- Preserve fail-fast behavior for missing required identity keys and explicit rejection accounting.
- Keep data lineage and run-level observability aligned with existing operational telemetry.

**Non-Goals:**
- Introduce Gold/business aggregates in this change.
- Add new public API endpoints for domain exploration in this slice.
- Rebuild unrelated raw ingestion contracts or historical source registration behavior.

## Decisions

1. **Add dedicated normalized domain tables (`normalized_buyers`, `normalized_suppliers`, `normalized_categories`).**
   - Rationale: explicit domain entities reduce duplication and establish stable query contracts for later Gold work.
   - Alternatives considered:
   - Keep embedded attributes in transactional tables only: rejected, because it leaves canonical identity unresolved.
   - Skip categories and implement buyers/suppliers only: rejected, because category semantics are already part of the stage-gated expansion scope.

2. **Use deterministic identity keys with explicit precedence and fail-fast enforcement.**
   - Buyers: canonical identity from `codigo_unidad_compra` (transaction rows missing this key are rejected for buyer-domain writes and tracked as quality issues).
   - Suppliers: canonical identity from `codigo_proveedor`, with fallback to `rut_proveedor` using a typed key format (`codigo:<value>` or `rut:<value>`).
   - Categories: canonical identity from `codigo_categoria`.
   - Rationale: explicit precedence avoids non-deterministic matching and makes replay idempotent.
   - Alternatives considered:
   - Best-effort fuzzy matching by names: rejected due to ambiguity and non-deterministic merges.

3. **Keep transactional normalized tables as source of truth for domain extraction in this slice.**
   - Rationale: avoids changing raw contracts and keeps this change localized to normalized build + schema.
   - Alternatives considered:
   - Build domain entities directly from raw tables: rejected for this stage because it duplicates normalization logic and increases blast radius.

4. **Apply domain population inside the normalized build flow after transactional upsert steps.**
   - Rationale: ensures source transactional rows are canonicalized before domain extraction and keeps run-level telemetry cohesive.
   - Alternatives considered:
   - Separate standalone pipeline command: rejected for this slice to avoid operator workflow fragmentation.

## Risks / Trade-offs

- **[Risk] Identity key sparsity may produce domain rejections in older datasets.** -> Mitigation: persist data quality issues with entity-specific counters and enforce deterministic gate policy.
- **[Risk] Additional domain upserts increase runtime cost for normalized builds.** -> Mitigation: chunked upserts, bounded checkpoints, and targeted indexes on domain keys.
- **[Risk] Mismatched migration/model definitions could reintroduce schema drift.** -> Mitigation: add migration/ORM parity checks and include them in quality validation.
- **[Risk] One-source buyer identity (`codigo_unidad_compra`) may miss licitacion-only contexts.** -> Mitigation: keep explicit out-of-scope note and track follow-up proposal if cross-source buyer identity unification is required.

## Migration Plan

1. Add Alembic migration for new domain tables, constraints, and indexes.
2. Add ORM models and relationships/foreign-key fields required for deterministic joins.
3. Add domain extract/upsert helpers in normalized build flow and quality-issue persistence paths.
4. Add tests for identity-key derivation, fail-fast behavior, idempotent upsert, and relationship integrity.
5. Run validation gates and capture controlled-run evidence before implementation archive.

Rollback strategy:
- Revert domain extraction write path and rollback migration to remove newly introduced domain tables and foreign-key contracts if acceptance criteria fail.

## Open Questions

None.

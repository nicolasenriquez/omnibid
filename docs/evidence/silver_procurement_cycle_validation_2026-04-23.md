# Silver Procurement Cycle Validation Evidence (2026-04-23)

Scope:
- OpenSpec change: `expand-silver-procurement-cycle-and-feature-foundation-2026-04-22`
- Milestone gates validated: Tasks 4.1, 4.2, 5.1, 5.2, 6.1

## Commands Executed

1. Quality gate:
```bash
just quality
```

Result:
- `ruff`: pass
- `mypy`: pass
- `pytest -m "not integration"`: `118 passed, 2 skipped`

2. Migration bootstrap:
```bash
just db-bootstrap
```

Result:
- initial run failed due Alembic revision id length constraint (`alembic_version.version_num VARCHAR(32)`)
- fix applied: shortened revision id `202604230020_silver_master_bridge` -> `202604230020_silver_master`
- dependent `down_revision` updated in `202604230030_silver_deterministic_enrichment.py`
- rerun succeeded through head:
  - `202604230010_silver_core`
  - `202604230020_silver_master`
  - `202604230030_silver_enrichment`
  - `202604230040_silver_text_ann`

3. Controlled normalized pipeline validation (licitaciones):
```bash
uv run python scripts/build_normalized.py \
  --dataset licitacion \
  --limit-rows 50 \
  --fetch-size 50 \
  --chunk-size 25 \
  --no-progress --no-resume --no-incremental \
  --state-path /tmp/silver_stage_validation_state.json \
  --reset-state
```

Result highlights:
- completed successfully
- processed `50` rows
- Silver annotations were written deterministically:
  - `notice_text_ann_deduplicated=11`
  - `notice_line_text_ann_deduplicated=21`

4. Controlled normalized pipeline validation (ordenes_compra):
```bash
uv run python scripts/build_normalized.py \
  --dataset orden_compra \
  --limit-rows 50 \
  --fetch-size 50 \
  --chunk-size 25 \
  --no-progress --no-resume --no-incremental \
  --state-path /tmp/silver_stage_validation_state.json \
  --reset-state
```

Result highlights:
- completed successfully
- processed `50` rows
- Silver annotation writes present:
  - `purchase_order_line_text_ann_deduplicated=50`

## Targeted Unit Validation for New Scope

Executed:
```bash
uv run pytest -q \
  tests/unit/test_silver_transform_builders.py \
  tests/unit/test_normalized_domain_entities_tdd.py \
  tests/unit/test_silver_text_annotation_schema_parity.py \
  tests/unit/test_silver_core_schema_parity.py \
  tests/unit/test_silver_master_bridge_schema_parity.py
```

Result:
- `59 passed`

## Conclusion

- Task 6.1 validation gate is satisfied:
  - quality gate green
  - controlled pipeline runs completed for both datasets
  - evidence captured in this file

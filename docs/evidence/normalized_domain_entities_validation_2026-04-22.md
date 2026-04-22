# Normalized Domain Entities Validation

Date: 2026-04-22  
Change: `expand-normalized-domain-buyers-suppliers-categories`

## Scope

Validate buyer/supplier/category canonical-domain integration in normalized build flow with:
- deterministic upsert behavior
- domain rejection telemetry
- replay idempotency

## Commands Run

1. Unit gate:

```bash
just test-unit
```

Result:
- `62 passed, 2 skipped`

2. Controlled normalized run (bounded sample over existing raw tables):

```bash
uv run python scripts/build_normalized.py \
  --dataset all \
  --fetch-size 500 \
  --chunk-size 200 \
  --limit-rows 2000 \
  --state-path data/runtime/normalized_domain_validation_state.json \
  --reset-state \
  --no-resume \
  --no-incremental
```

Key output highlights:
- licitaciones domain metrics:
  - `suppliers{accepted=2,000 deduplicated=397 inserted_delta=0 existing_or_updated=397 rejected=0}`
- ordenes_compra domain metrics:
  - `buyers{accepted=2,000 deduplicated=282 inserted_delta=121 existing_or_updated=161 rejected=0}`
  - `suppliers{accepted=2,000 deduplicated=572 inserted_delta=107 existing_or_updated=465 rejected=0}`
  - `categories{accepted=1,982 deduplicated=471 inserted_delta=250 existing_or_updated=221 rejected=18}`

3. Replay idempotency run (same bounded input):

```bash
uv run python scripts/build_normalized.py \
  --dataset all \
  --fetch-size 500 \
  --chunk-size 200 \
  --limit-rows 2000 \
  --state-path data/runtime/normalized_domain_validation_state.json \
  --no-resume \
  --no-incremental
```

Replay highlights:
- licitaciones domain metrics:
  - `suppliers{... inserted_delta=0 ...}`
- ordenes_compra domain metrics:
  - `buyers{... inserted_delta=0 ...}`
  - `suppliers{... inserted_delta=0 ...}`
  - `categories{... inserted_delta=0 ... rejected=18}`

Conclusion:
- replay converges without duplicate semantic inserts for new domain entities.

4. Post-run DB verification:

```bash
uv run python - <<'PY'
import sqlalchemy as sa
from backend.db.session import SessionLocal
from backend.models.normalized import NormalizedBuyer, NormalizedSupplier, NormalizedCategory
from backend.models.operational import DataQualityIssue

with SessionLocal() as s:
    print("normalized_buyers", s.execute(sa.select(sa.func.count()).select_from(NormalizedBuyer)).scalar_one())
    print("normalized_suppliers", s.execute(sa.select(sa.func.count()).select_from(NormalizedSupplier)).scalar_one())
    print("normalized_categories", s.execute(sa.select(sa.func.count()).select_from(NormalizedCategory)).scalar_one())
    print(
        "domain_identity_issues_total",
        s.execute(
            sa.select(sa.func.count())
            .select_from(DataQualityIssue)
            .where(DataQualityIssue.issue_type == "normalized_missing_domain_identity")
        ).scalar_one(),
    )
PY
```

Observed:
- `normalized_buyers=121`
- `normalized_suppliers=13583`
- `normalized_categories=250`
- `domain_identity_issues_total=2`

## Domain Rejection Evidence

Latest bounded `orden_compra` run emitted:
- issue type: `normalized_missing_domain_identity`
- `record_ref=categories`
- `column_name=codigo_categoria`
- `rejected_rows=18`
- `error_rate=0.009`

This confirms domain-specific rejection tracking is persisted with identity-column context.

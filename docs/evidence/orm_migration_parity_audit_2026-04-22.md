# ORM vs Migration Parity Audit (Task 2.1)

Date: 2026-04-22

## Scope

- Audit migration-defined index/constraint contracts for operational/raw tables.
- Compare against current SQLAlchemy model metadata declarations.

## Sources Reviewed

- `alembic/versions/0001_operational_and_bronze.py`
- `alembic/versions/0004_rename_raw_norm_tables.py`
- `backend/models/operational.py`
- `backend/models/raw.py`

## Expected Index Contracts from Migrations

Operational:

- `ix_source_files_dataset_type` on `source_files(dataset_type)`
- `ix_pipeline_runs_status` on `pipeline_runs(status)`
- `ix_pipeline_run_steps_run_id` on `pipeline_run_steps(run_id)`

Raw (renamed from bronze by 0004):

- `ix_raw_licitaciones_codigo_externo` on `raw_licitaciones(codigo_externo)`
- `ix_raw_ordenes_compra_codigo_oc` on `raw_ordenes_compra(codigo_oc)`
- `ix_raw_ordenes_compra_codigo_licitacion` on `raw_ordenes_compra(codigo_licitacion)`

## Current ORM Metadata Snapshot

Observed via model metadata inspection:

- `SourceFile.__table__.indexes`: none
- `PipelineRun.__table__.indexes`: none
- `PipelineRunStep.__table__.indexes`: none
- `RawLicitacion.__table__.indexes`: none
- `RawOrdenCompra.__table__.indexes`: none

## Parity Findings

- Migration index contracts exist for operational/raw tables, but equivalent index declarations are currently missing in ORM metadata.
- Existing raw unique constraints are present (`uq_raw_lic_raw_file_row`, `uq_raw_oc_raw_file_row`) and aligned.

## Conclusion

Parity gap confirmed for migration-defined indexes in operational/raw model metadata. Task `2.2` should add explicit index declarations in `backend/models/operational.py` and `backend/models/raw.py` to align metadata with migrated schema intent.

## Parity Sanity Check (Task 2.3)

Autogenerate check executed after model parity updates:

- command: `UV_NO_SYNC=1 ./.venv/bin/alembic revision --autogenerate -m parity_sanity_tmp_20260422`
- generated temporary revision: `alembic/versions/526663ff72af_parity_sanity_tmp_20260422.py`
- upgrade/downgrade bodies: `pass` only (no schema operations)
- result: no unintended schema churn detected
- cleanup: temporary revision file removed after inspection

## Re-Validation During Task 5.1

Autogenerate parity sanity re-run after completing reliability hardening:

- command: `uv run alembic revision --autogenerate -m "tmp_reliability_parity_check"`
- generated temporary revision: `alembic/versions/915449131776_tmp_reliability_parity_check.py`
- upgrade/downgrade bodies: `pass` only (no schema operations)
- result: no unintended schema churn detected
- cleanup: temporary revision file removed after inspection

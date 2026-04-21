set shell := ["bash", "-euo", "pipefail", "-c"]

# ============================================================
# Canonical Commands (grouped + documented)
# ============================================================

[group('00 Base')]
[doc('List available commands grouped by area')]
default:
    @just --list

[group('01 Setup')]
[doc('Install and sync project dependencies with uv')]
setup:
    command -v uv >/dev/null 2>&1 || (echo "uv is required. Install: https://docs.astral.sh/uv/" && exit 1)
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv sync --extra dev

[group('01 Setup')]
[doc('Sync local Codex workspace files')]
codex-sync:
    ./scripts/sync_codex_dir.sh

[group('02 Runtime')]
[doc('Run FastAPI in local dev mode (guarded against test DB)')]
api: db-runtime-guard
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

[group('03 Quality')]
[doc('Format code with Ruff')]
fmt:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run ruff format backend tests scripts

[group('03 Quality')]
[doc('Run Ruff lint checks')]
lint:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run ruff check backend tests scripts

[group('03 Quality')]
[doc('Run MyPy type checks')]
type:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run mypy backend scripts

[group('03 Quality')]
[doc('Format code with Black')]
black:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run black backend tests scripts

[group('03 Quality')]
[doc('Check Black formatting without modifying files')]
black-check:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run black backend tests scripts --check --diff --workers 1

[group('03 Quality')]
[doc('Run strict type gates (Pyright + ty)')]
type-strict:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run pyright backend scripts
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run ty check backend

[group('03 Quality')]
[doc('Run high-confidence/high-severity security checks')]
security:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run bandit -c pyproject.toml -r backend --severity-level high --confidence-level high

[group('03 Quality')]
[doc('Run default test suite (unit tests)')]
test: test-unit

[group('03 Quality')]
[doc('Run unit tests only')]
test-unit:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run pytest -q -m "not integration"

[group('03 Quality')]
[doc('Run unit tests using local .venv (fallback when uv is restricted)')]
test-unit-local:
    ./.venv/bin/pytest -q -m "not integration"

[group('03 Quality')]
[doc('Run integration tests against TEST_DATABASE_URL')]
test-integration: test-db-check
    #!/usr/bin/env bash
    test_url="${TEST_DATABASE_URL:-}"
    if [[ -z "$test_url" ]] && [[ -f .env ]]; then
      test_url="$(grep -E '^[[:space:]]*TEST_DATABASE_URL=' .env | tail -n 1 | cut -d '=' -f2- || true)"
      test_url="${test_url%\"}"
      test_url="${test_url#\"}"
      test_url="${test_url%\'}"
      test_url="${test_url#\'}"
    fi
    DATABASE_URL="$test_url" UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run pytest -q -m "integration"

[group('03 Quality')]
[doc('Fast local quality gate: lint + type + unit tests')]
quality: ci-fast

[group('03 Quality')]
[doc('Fast CI gate: lint + type + unit tests')]
ci-fast: lint type test-unit

[group('03 Quality')]
[doc('Full CI gate: fast gate + strict type + security + integration')]
ci: ci-fast black-check type-strict security test-integration

[group('04 Database')]
[doc('Fail if DATABASE_URL is missing or points to a *_test DB')]
db-runtime-guard:
    #!/usr/bin/env bash
    raw_url="${DATABASE_URL:-}"
    if [[ -z "$raw_url" ]] && [[ -f .env ]]; then
      raw_url="$(grep -E '^[[:space:]]*DATABASE_URL=' .env | tail -n 1 | cut -d '=' -f2- || true)"
      raw_url="${raw_url%\"}"
      raw_url="${raw_url#\"}"
      raw_url="${raw_url%\'}"
      raw_url="${raw_url#\'}"
    fi

    if [[ -z "$raw_url" ]]; then
      echo "DATABASE_URL is not set."
      exit 1
    fi

    db_name="${raw_url##*/}"
    db_name="${db_name%%\?*}"
    if [[ "$db_name" == *_test ]]; then
      echo "Refusing runtime against test DB: ${db_name}"
      exit 1
    fi

    echo "Runtime DB guard passed: ${db_name}"

[group('04 Database')]
[doc('Fail if TEST_DATABASE_URL is missing or equals DATABASE_URL')]
test-db-check:
    #!/usr/bin/env bash
    test_url="${TEST_DATABASE_URL:-}"
    if [[ -z "$test_url" ]] && [[ -f .env ]]; then
      test_url="$(grep -E '^[[:space:]]*TEST_DATABASE_URL=' .env | tail -n 1 | cut -d '=' -f2- || true)"
      test_url="${test_url%\"}"
      test_url="${test_url#\"}"
      test_url="${test_url%\'}"
      test_url="${test_url#\'}"
    fi

    if [[ -z "$test_url" ]]; then
      echo "TEST_DATABASE_URL is not set."
      exit 1
    fi

    runtime_url="${DATABASE_URL:-}"
    if [[ -z "$runtime_url" ]] && [[ -f .env ]]; then
      runtime_url="$(grep -E '^[[:space:]]*DATABASE_URL=' .env | tail -n 1 | cut -d '=' -f2- || true)"
      runtime_url="${runtime_url%\"}"
      runtime_url="${runtime_url#\"}"
      runtime_url="${runtime_url%\'}"
      runtime_url="${runtime_url#\'}"
    fi

    if [[ -n "$runtime_url" ]] && [[ "$runtime_url" == "$test_url" ]]; then
      echo "TEST_DATABASE_URL must differ from DATABASE_URL"
      exit 1
    fi

    echo "Test DB check passed"

[group('04 Database')]
[doc('Create a new Alembic migration revision')]
db-revision name:
    #!/usr/bin/env bash
    set -euo pipefail
    slug="$(printf '%s' "{{name}}" | tr '[:upper:]' '[:lower:]' | tr ' /' '__' | tr -cd 'a-z0-9_' | cut -c1-17)"
    rev_id="$(date +%Y%m%d%H%M%S)_${slug}"
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run alembic revision --rev-id "$rev_id" -m "{{name}}"

[group('04 Database')]
[doc('Create runtime database if missing')]
db-create:
    #!/usr/bin/env bash
    raw_url="${DATABASE_URL:-postgresql+psycopg://postgres:postgres@localhost:5432/chilecompra}"
    time UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" DATABASE_URL="$raw_url" uv run python - <<'PY'
    import os
    import sys
    from sqlalchemy import text
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import create_async_engine
    import asyncio

    def escape_identifier(value: str) -> str:
        return value.replace('"', '""')

    async def main() -> int:
        raw_url = os.environ["DATABASE_URL"]
        target = make_url(raw_url)
        target_db = target.database
        if not target_db:
            print("DATABASE_URL must include a database name.", file=sys.stderr)
            return 1

        admin_db = os.environ.get("DATABASE_ADMIN_DB", "postgres")
        admin_url = target.set(database=admin_db)
        engine = create_async_engine(str(admin_url), isolation_level="AUTOCOMMIT")
        try:
            async with engine.connect() as conn:
                exists = (
                    await conn.execute(
                        text("SELECT 1 FROM pg_database WHERE datname = :db"),
                        {"db": target_db},
                    )
                ).scalar_one_or_none()

                if exists is None:
                    await conn.execute(text(f'CREATE DATABASE "{escape_identifier(target_db)}"'))
                    print(f"Created database: {target_db}")
                else:
                    print(f"Database already exists: {target_db}")
        finally:
            await engine.dispose()

        return 0

    raise SystemExit(asyncio.run(main()))
    PY

[group('04 Database')]
[doc('Apply Alembic migrations to head')]
db-migrate:
    time UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run alembic upgrade head

[group('04 Database')]
[doc('Create DB and apply migrations')]
db-bootstrap: db-create db-migrate

[group('05 Raw')]
[doc('Profile source CSV files from DATASET_ROOT')]
raw-profile:
    time UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run python scripts/profile_raw.py --dataset-root "${DATASET_ROOT:-}"

[group('05 Raw')]
[doc('Ingest raw source files into raw tables')]
raw-ingest:
    time UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run python scripts/ingest_raw.py --dataset-root "${DATASET_ROOT:-}" --chunk-size "${CHUNK_SIZE:-5000}" --limit-files "${LIMIT_FILES:-0}"

[group('05 Raw')]
[doc('Fast raw ingest (skip progress bars and pre-count)')]
raw-ingest-fast:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run python scripts/ingest_raw.py --dataset-root "${DATASET_ROOT:-}" --chunk-size "${CHUNK_SIZE:-5000}" --limit-files "${LIMIT_FILES:-0}" --no-progress --no-precount

[group('06 Normalized')]
[doc('Build normalized layer incrementally from raw data (default mode)')]
normalized-build:
    time UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run python scripts/build_normalized.py --dataset "${NORMALIZED_DATASET:-all}" --fetch-size "${NORMALIZED_FETCH_SIZE:-10000}" --chunk-size "${NORMALIZED_CHUNK_SIZE:-500}" --limit-rows "${NORMALIZED_LIMIT_ROWS:-0}" --state-path "${NORMALIZED_STATE_PATH:-data/runtime/normalized_build_state.json}"

[group('06 Normalized')]
[doc('Build normalized layer with full refresh semantics (no incremental, no resume)')]
normalized-full:
    time UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run python scripts/build_normalized.py --dataset "${NORMALIZED_DATASET:-all}" --fetch-size "${NORMALIZED_FETCH_SIZE:-10000}" --chunk-size "${NORMALIZED_CHUNK_SIZE:-500}" --limit-rows "${NORMALIZED_LIMIT_ROWS:-0}" --state-path "${NORMALIZED_STATE_PATH:-data/runtime/normalized_build_state.json}" --no-incremental --no-resume

[group('06 Normalized')]
[doc('Reset normalized state checkpoint file before the next run')]
normalized-reset:
    time UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run python scripts/build_normalized.py --dataset "${NORMALIZED_DATASET:-all}" --fetch-size "${NORMALIZED_FETCH_SIZE:-10000}" --chunk-size "${NORMALIZED_CHUNK_SIZE:-500}" --limit-rows "${NORMALIZED_LIMIT_ROWS:-0}" --state-path "${NORMALIZED_STATE_PATH:-data/runtime/normalized_build_state.json}" --reset-state

[group('06 Normalized')]
[doc('Build normalized layer only for licitaciones dataset')]
normalized-lic:
    NORMALIZED_DATASET=licitacion just normalized-build

[group('06 Normalized')]
[doc('Build normalized layer only for ordenes_compra dataset')]
normalized-oc:
    NORMALIZED_DATASET=orden_compra just normalized-build

[group('07 Pipelines')]
[doc('Raw pipeline: db-bootstrap -> raw-profile -> raw-ingest')]
pipeline-raw: db-bootstrap raw-profile raw-ingest

[group('07 Pipelines')]
[doc('Raw fast pipeline: db-bootstrap -> raw-ingest')]
pipeline-raw-fast: db-bootstrap raw-ingest

[group('07 Pipelines')]
[doc('Normalized pipeline from existing raw data: db-migrate -> normalized-build')]
pipeline-normalized: db-migrate normalized-build

[group('07 Pipelines')]
[doc('Full pipeline: pipeline-raw -> pipeline-normalized')]
pipeline-full: pipeline-raw pipeline-normalized

[group('07 Pipelines')]
[doc('Full fast pipeline: pipeline-raw-fast -> pipeline-normalized')]
pipeline-full-fast: pipeline-raw-fast pipeline-normalized

[group('08 Future')]
[doc('Placeholder for future Gold build')]
pipeline-gold:
    echo "TODO: implement gold build"

# ============================================================
# Legacy command names intentionally removed to keep the interface clean.

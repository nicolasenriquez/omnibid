set shell := ["bash", "-euo", "pipefail", "-c"]

# ============================================================
# Base
# ============================================================

default:
    @just --list

# ============================================================
# Setup / Sync
# ============================================================

setup:
    command -v uv >/dev/null 2>&1 || (echo "uv is required. Install: https://docs.astral.sh/uv/" && exit 1)
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv sync --extra dev

codex-sync:
    ./scripts/sync_codex_dir.sh

# ============================================================
# Runtime
# ============================================================

# Run FastAPI in local dev mode. Protected by runtime DB guard.
api: db-runtime-guard
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# ============================================================
# Code Quality
# ============================================================

fmt:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run ruff format backend tests scripts

lint:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run ruff check backend tests scripts

type:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run mypy backend scripts

black:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run black backend tests scripts

black-check:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run black backend tests scripts --check --diff --workers 1

type-strict:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run pyright backend scripts
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run ty check backend

security:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run bandit -c pyproject.toml -r backend --severity-level high --confidence-level high

# ============================================================
# Tests (TDD first)
# ============================================================

# Canonical local test command.
test: test-unit

test-unit:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run pytest -q -m "not integration"

# Fallback when uv cannot resolve deps due network restrictions.
test-unit-local:
    ./.venv/bin/pytest -q -m "not integration"

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

# Fast local quality gate (recommended before commit).
quality: backend-ci-fast
ci-fast: backend-ci-fast
backend-ci-fast: lint type test-unit

# Full local CI gate.
backend-ci: backend-ci-fast black-check type-strict security test-integration
ci: backend-ci

# ============================================================
# DB Guards (fail-fast safety)
# ============================================================

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

# ============================================================
# DB Schema / Migrations
# ============================================================

db-revision name:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run alembic revision -m "{{name}}"

db-create:
    #!/usr/bin/env bash
    raw_url="${DATABASE_URL:-postgresql+psycopg://postgres:postgres@localhost:5432/chilecompra}"
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" DATABASE_URL="$raw_url" uv run python - <<'PY'
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

db-upgrade:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run alembic upgrade head

# Canonical DB bootstrap for local development.
db-bootstrap: db-create db-upgrade

# ============================================================
# Data Pipeline: Bronze
# ============================================================

profile-files:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run python scripts/profile_files.py --dataset-root "${DATASET_ROOT:-}"

ingest-raw:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run python scripts/ingest_raw.py --dataset-root "${DATASET_ROOT:-}" --chunk-size "${CHUNK_SIZE:-5000}" --limit-files "${LIMIT_FILES:-0}"

ingest-raw-fast:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run python scripts/ingest_raw.py --dataset-root "${DATASET_ROOT:-}" --chunk-size "${CHUNK_SIZE:-5000}" --limit-files "${LIMIT_FILES:-0}" --no-progress --no-precount

build-bronze:
    just ingest-raw

# Canonical step 1 (Bronze): profile + ingest raw.
pipeline-1-bronze: db-bootstrap profile-files ingest-raw

# Faster variant: skip profiling.
pipeline-1-bronze-fast: db-bootstrap ingest-raw

# ============================================================
# Data Pipeline: Silver / Gold
# ============================================================

build-silver:
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run python scripts/build_silver.py --dataset "${SILVER_DATASET:-all}" --fetch-size "${SILVER_FETCH_SIZE:-10000}" --chunk-size "${SILVER_CHUNK_SIZE:-2000}" --limit-rows "${SILVER_LIMIT_ROWS:-0}"

# Canonical step 2 (Silver): build Silver using already-ingested Bronze data.
pipeline-2-silver-from-bronze: db-bootstrap build-silver

build-gold:
    echo "TODO: implement gold build"

# Canonical step 3 (Gold): placeholder for future.
pipeline-3-gold: build-gold

# Canonical end-to-end execution: Bronze -> Silver.
pipeline-all: pipeline-1-bronze pipeline-2-silver-from-bronze

# Faster end-to-end: Bronze(no profile) -> Silver.
pipeline-all-fast: pipeline-1-bronze-fast pipeline-2-silver-from-bronze

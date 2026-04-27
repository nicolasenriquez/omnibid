set shell := ["bash", "-euo", "pipefail", "-c"]
set windows-shell := ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"]
set export

UV_CACHE_DIR := env_var_or_default("UV_CACHE_DIR", ".uv-cache")
CHUNK_SIZE := env_var_or_default("CHUNK_SIZE", "5000")
NORMALIZED_DATASET := env_var_or_default("NORMALIZED_DATASET", "all")
NORMALIZED_FETCH_SIZE := env_var_or_default("NORMALIZED_FETCH_SIZE", "10000")
NORMALIZED_CHUNK_SIZE := env_var_or_default("NORMALIZED_CHUNK_SIZE", "500")
NORMALIZED_LIMIT_ROWS := env_var_or_default("NORMALIZED_LIMIT_ROWS", "0")
NORMALIZED_STATE_PATH := env_var_or_default("NORMALIZED_STATE_PATH", "data/runtime/normalized_build_state.json")
NORMALIZED_STATE_CHECKPOINT_EVERY_PAGES := env_var_or_default("NORMALIZED_STATE_CHECKPOINT_EVERY_PAGES", "1")
LOCAL_VENV_PYTHON := if os() == "windows" { ".venv/Scripts/python.exe" } else { ".venv/bin/python" }
SPINNER_RUNNER := "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/run_with_spinner.ps1"

# ============================================================
# Canonical Commands (Docker-first)
# ============================================================

[group('01 Setup')]
[doc('Containerized dependency bootstrap (no host uv required)')]
uv-sync: docker-build

[group('01 Setup')]
[doc('Optional host dependency sync (requires uv in PATH)')]
uv-sync-host:
    uv --version
    uv sync --extra dev

[group('02 Quality')]
[doc('Format code with Ruff')]
fmt:
    uv run ruff format backend tests scripts

[group('02 Quality')]
[doc('Run Ruff lint checks')]
lint:
    uv run ruff check backend tests scripts

[group('02 Quality')]
[doc('Run MyPy type checks')]
type:
    uv run mypy backend scripts

[group('02 Quality')]
[doc('Format code with Black')]
black:
    uv run black backend tests scripts

[group('02 Quality')]
[doc('Run strict type gates (Pyright + ty)')]
type-strict:
    uv run pyright backend scripts
    uv run ty check backend

[group('02 Quality')]
[doc('Run high-confidence/high-severity security checks')]
security:
    uv run bandit -c pyproject.toml -r backend --severity-level high --confidence-level high

[group('02 Quality')]
[doc('Run default test suite (unit tests)')]
test: test-unit

[group('02 Quality')]
[doc('Run unit tests only')]
test-unit:
    uv run pytest -q -m "not integration"

[group('02 Quality')]
[doc('Run unit tests using local .venv (fallback when uv is restricted)')]
test-unit-local:
    {{LOCAL_VENV_PYTHON}} -m pytest -q -m "not integration"

[group('02 Quality')]
[private]
[doc('Fail if TEST_DATABASE_URL is missing or equals DATABASE_URL')]
test-db-check:
    uv run python scripts/test_db_guard.py check

[group('02 Quality')]
[doc('Run integration tests against TEST_DATABASE_URL')]
test-integration: test-db-check
    uv run python scripts/test_db_guard.py run-integration

[group('02 Quality')]
[doc('Fast local quality gate: lint + type + unit tests')]
quality: ci-fast

[group('02 Quality')]
[doc('Fast CI gate: lint + type + unit tests')]
ci-fast: lint type test-unit

[group('02 Quality')]
[doc('Full CI gate: fast gate + strict type + security + integration')]
ci: ci-fast type-strict security test-integration

[group('03 Docker')]
[private]
[doc('Build Docker images for local backend stack')]
docker-build:
    @{{SPINNER_RUNNER}} -Message "Docker: building backend image" -CommandText "docker compose --env-file .env.docker -f docker-compose.yml build"

[group('03 Docker')]
[private]
[doc('Start Docker PostgreSQL service only')]
docker-db-up:
    @{{SPINNER_RUNNER}} -Message "Docker: starting db service" -CommandText "docker compose --env-file .env.docker -f docker-compose.yml up -d db"

[group('03 Docker')]
[private]
[doc('Apply Alembic migrations in Docker backend container')]
docker-migrate: docker-db-up
    @{{SPINNER_RUNNER}} -Message "Docker: applying migrations" -CommandText "docker compose --env-file .env.docker -f docker-compose.yml run --rm backend uv run --no-sync alembic upgrade head"

[group('03 Docker')]
[private]
[doc('Bootstrap Docker PostgreSQL + migrations')]
docker-bootstrap: docker-db-up docker-migrate

[group('03 Docker')]
[doc('One-command startup: build image, bootstrap DB, and start backend in background')]
docker-start: docker-build docker-bootstrap
    @{{SPINNER_RUNNER}} -Message "Docker: starting backend service" -CommandText "docker compose --env-file .env.docker -f docker-compose.yml up -d backend"

[group('04 Docker Ops')]
[private]
[doc('Run raw profile + ingest pipeline in Docker backend container')]
docker-pipeline-raw: docker-db-up
    docker compose --env-file .env.docker -f docker-compose.yml run --rm --no-deps -e PROGRESS_FORCE_TTY=1 backend uv run --no-sync python scripts/profile_raw.py
    docker compose --env-file .env.docker -f docker-compose.yml run --rm --no-deps -e PROGRESS_FORCE_TTY=1 backend uv run --no-sync python scripts/ingest_raw.py --chunk-size "{{CHUNK_SIZE}}"

[group('04 Docker Ops')]
[private]
[doc('Run normalized pipeline in Docker backend container')]
docker-pipeline-normalized: docker-db-up
    docker compose --env-file .env.docker -f docker-compose.yml run --rm --no-deps -e PROGRESS_FORCE_TTY=1 backend uv run --no-sync python scripts/build_normalized.py --dataset "{{NORMALIZED_DATASET}}" --fetch-size "{{NORMALIZED_FETCH_SIZE}}" --chunk-size "{{NORMALIZED_CHUNK_SIZE}}" --limit-rows "{{NORMALIZED_LIMIT_ROWS}}" --state-path "{{NORMALIZED_STATE_PATH}}" --state-checkpoint-every-pages "{{NORMALIZED_STATE_CHECKPOINT_EVERY_PAGES}}"

[group('04 Docker Ops')]
[doc('Run full Docker pipeline: raw then normalized')]
docker-pipeline-full: docker-pipeline-raw docker-pipeline-normalized

[group('04 Docker Ops')]
[doc('Smoke check Docker backend health and running services')]
docker-smoke:
    docker compose --env-file .env.docker -f docker-compose.yml ps
    docker compose --env-file .env.docker -f docker-compose.yml exec -T backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read().decode())"

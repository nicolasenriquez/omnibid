# GitHub Actions CI Runbook (Container-First)

## Purpose

Operational runbook for implementing and maintaining GitHub Actions CI with Docker-container-first execution in this repository.

## Prerequisites

1. Repository has valid Dockerfile, compose file, and `justfile` gate recipes.
2. GitHub Actions is enabled for repository.
3. Branch protection/ruleset owner is identified for `main`.

## Execution Order (Waterfall)

Complete each stage before unlocking next.

### Stage 1: Documentation and Source Validation

1. Create/update SDD reference note for CI/CD decisions.
2. Update standards and runbook documentation.
3. Verify official source links are current and accessible.

Exit criteria:

- Docs merged with explicit source mapping.

### Stage 2: Workflow Baseline

1. Add `.github/workflows/ci.yml`.
2. Add jobs:
   - `Secret Scan`
   - `Backend Gates`
   - `Frontend Gates`
3. Pin actions by full SHA and set least-privilege permissions.

Exit criteria:

- Workflow YAML is valid.
- Required jobs are present and named uniquely.

### Stage 3: Dependency and PR Governance

1. Add `.github/dependabot.yml`.
2. Add `.github/pull_request_template.md`.

Exit criteria:

- Dependabot config covers `uv`, `npm` (`/client`), and `github-actions`.
- PR template includes validation checklist and command log section.

### Stage 4: Local Security and Quality Parity

1. Add `.gitleaks.toml`.
2. Add `.pre-commit-config.yaml`.
3. Add helper scripts for secret scanning.

Exit criteria:

- Local pre-push flow can run equivalent checks to CI (without changing gate semantics).

### Stage 5: Branch Protection Activation

1. Configure required checks on `main`:
   - `Secret Scan`
   - `Backend Gates`
   - `Frontend Gates`
2. Require pull request before merge.

Exit criteria:

- Direct merge to `main` blocked unless required checks pass.

## Backend Gate Command Contract

Backend validation should align with container-first recipes:

1. `docker compose --env-file .env.docker -f docker-compose.yml build backend-tools`
2. `docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync ruff check backend tests scripts`
3. `docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync mypy backend scripts`
4. `docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync pytest -q -m "not integration"`
5. strict/security/integration equivalents from `just ci`.

If `DATASET_HOST_PATH` from `.env.docker` is machine-specific, override it in CI to repository-local path before compose commands.

## Frontend Gate Command Contract

Run in containerized environment with project scripts:

1. `npm ci`
2. `npm run lint`
3. `npm run typecheck`
4. `npm run build`

## Security Controls Checklist

1. `permissions` set to read-only by default.
2. Only required jobs get additional write permissions.
3. Action references pinned to commit SHAs.
4. Secret scan gate enabled before backend/frontend gates are trusted.
5. No broad allowlists in gitleaks configuration.

## Troubleshooting

### CI fails due dataset mount path

- Symptom: compose volume path invalid on GitHub runner.
- Fix: set `DATASET_HOST_PATH=${{ github.workspace }}/data/datasets/mercado-publico` (or equivalent) in workflow step env.

### Ambiguous required status checks

- Symptom: merge blocked with duplicated check names.
- Fix: ensure unique job names across workflows.

### Integration tests fail due test DB collision

- Symptom: guard script rejects DB URLs.
- Fix: preserve `DATABASE_URL` and `TEST_DATABASE_URL` separation; keep test profile service isolated.

## Official References

- GitHub workflow syntax:
  - https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- GitHub service containers:
  - https://docs.github.com/en/actions/guides/about-service-containers
- GitHub security hardening:
  - https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions
- GitHub token permissions:
  - https://docs.github.com/en/actions/security-guides/automatic-token-authentication
- About protected branches:
  - https://docs.github.com/github/administering-a-repository/about-protected-branches
- Docker Compose:
  - https://docs.docker.com/compose/
  - https://docs.docker.com/compose/how-tos/profiles/

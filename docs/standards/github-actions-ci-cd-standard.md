# GitHub Actions CI Standard (Container-First)

## Purpose

Define secure, reproducible, and long-term CI baseline for this repository using GitHub Actions while preserving Docker-container-first execution.

## Scope

- `.github/workflows/*.yml`
- `.github/dependabot.yml`
- `.github/pull_request_template.md`
- supporting security and local quality artifacts (`.gitleaks.toml`, `.pre-commit-config.yaml`, `scripts/security/*`)

## Out Of Scope

- CD deployment workflows
- image publishing registries
- environment promotion rules

## Non-Negotiable Principles

1. Container-first execution for backend, DB, migrations, pipeline, and quality gates.
2. Fail-fast required checks; no warning-only downgrade for mandatory gates.
3. Least-privilege `GITHUB_TOKEN` permissions by default.
4. Immutable action references: pin third-party actions to full commit SHAs.
5. Source-driven decisions only: workflow features must map to official docs.

## Required Gate Model

Required checks on pull requests targeting `main`:

1. `Secret Scan`
2. `Backend Gates`
3. `Frontend Gates`

All required checks must pass before merge (branch protection/ruleset policy).

## Workflow Requirements

### Triggering

- Required events:
  - `pull_request` on `main`
  - `push` on `main`
- Optional:
  - `workflow_dispatch` for explicit manual suites.

### Concurrency

- Use workflow-level `concurrency` to cancel stale runs on the same ref.
- Pattern:
  - `group: ${{ github.workflow }}-${{ github.ref }}`
  - `cancel-in-progress: true`

### Permissions

- Set workflow default:
  - `permissions: { contents: read }`
- Elevate per-job only when required (example: PR annotation jobs needing `pull-requests: write`).

### Action Pinning

- `uses:` entries must pin full commit SHA.
- Tag-only references are discouraged for required checks.
- Refresh pinned SHAs through controlled update process (Dependabot + review).

## Container-First Enforcement

Backend CI gate must execute through Docker Compose and existing repository contract:

- Prefer `just ci-fast` and `just ci` composition.
- If `just` is not used in workflow, commands must remain equivalent to Docker-backed recipes.
- Host-local `uv run` backend validation in Actions is fallback only, not default.

Frontend CI gate:

- Preferred: run via containerized Node/Playwright image or equivalent containerized runner.
- Avoid host-local Node as default CI path.

## Security Standards

1. Secret scanning required on every PR and push to `main`.
2. Local allowlists must be narrow, file-scoped, and justified in config comments.
3. Never grant write permissions broadly at workflow root.
4. Keep CI runtime variables explicit; avoid implicit secrets propagation.
5. Keep ports local-only in compose and avoid privileged containers.

## Dependency Automation Standards

Dependabot must manage:

1. `uv` ecosystem in repository root.
2. `npm` ecosystem in `/client`.
3. `github-actions` ecosystem in root.

Guidelines:

- Weekly cadence.
- Group patch/minor updates to reduce noise.
- Group security updates explicitly.
- Keep PR limits bounded.

## PR Governance

PR template must capture:

1. Change summary and scope.
2. Exact validation commands run.
3. Risk and rollback notes.
4. Explicit explanation when a required gate is intentionally deferred.

## Waterfall Rollout Rule

Implement CI in short stages. Each stage must complete and validate before the next stage:

1. SDD references and standards documentation.
2. Workflow implementation.
3. Dependabot and PR governance.
4. Local hook/security parity.
5. Branch protection/ruleset activation.

## Official Sources

- GitHub workflow syntax:
  - https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- GitHub workflow triggers and dispatch inputs:
  - https://docs.github.com/en/actions/using-workflows/triggering-a-workflow
- GitHub Actions token permissions:
  - https://docs.github.com/en/actions/security-guides/automatic-token-authentication
- GitHub Actions security hardening:
  - https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions
- GitHub service containers:
  - https://docs.github.com/en/actions/guides/about-service-containers
- Dependabot supported ecosystems:
  - https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-and-repositories
- Dependabot options:
  - https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference
- pre-commit:
  - https://pre-commit.com/
- Gitleaks Action:
  - https://github.com/gitleaks/gitleaks-action
- Docker Compose:
  - https://docs.docker.com/compose/
  - https://docs.docker.com/compose/how-tos/profiles/
  - https://docs.docker.com/compose/how-tos/environment-variables/envvars/

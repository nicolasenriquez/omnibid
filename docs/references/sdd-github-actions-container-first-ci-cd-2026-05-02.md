# SDD Reference: GitHub Actions CI/CD (Container-First) for Omnibid

## Metadata

- Change/Proposal: CI/CD bootstrap for `.github/` in `app-chilecompra`
- Date: 2026-05-02
- Author: Codex
- Area: CI/CD, security, dependency automation, Docker-first operations

## Question

- How do we implement secure and professional GitHub CI/CD in this repository while preserving the existing Docker-container-first execution model?

## Official Sources Consulted

1. GitHub Actions workflow syntax
   - URL: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
   - Relevant contract:
     - Workflow files live in `.github/workflows`.
     - `permissions`, `concurrency`, `on.push`, `on.pull_request`, and `workflow_dispatch` inputs are first-class supported syntax.

2. GitHub Actions trigger behavior and `workflow_dispatch` input types
   - URL: https://docs.github.com/en/actions/using-workflows/triggering-a-workflow
   - Relevant contract:
     - `workflow_dispatch` supports typed inputs including `choice`.
     - Inputs are available via `inputs` and `github.event.inputs`.

3. GitHub Actions `GITHUB_TOKEN` least-privilege guidance
   - URL: https://docs.github.com/en/actions/security-guides/automatic-token-authentication
   - Relevant contract:
     - Use `permissions` to grant minimum required access.
     - Least privilege is recommended baseline security posture.

4. GitHub Actions hardening guidance for third-party actions
   - URL: https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions
   - Relevant contract:
     - Pin actions to full commit SHA for immutable supply-chain references.

5. GitHub service containers communication model
   - URL: https://docs.github.com/en/actions/guides/about-service-containers
   - Relevant contract:
     - Jobs running on runner host can access services via `localhost:<port>`.
     - Linux runners are required for service containers.

6. Dependabot supported ecosystems
   - URL: https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-and-repositories
   - Relevant contract:
     - `uv`, `npm`, and `github-actions` ecosystems are supported.

7. Dependabot options and grouping controls
   - URL: https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference
   - Relevant contract:
     - `groups`, `open-pull-requests-limit`, schedules, labels, and grouped security updates are supported options.

8. Docker Compose usage in CI and environment parity
   - URL: https://docs.docker.com/compose/
   - Relevant contract:
     - Compose is supported for CI workflows and multi-service orchestration.

9. Docker Compose profiles behavior
   - URL: https://docs.docker.com/compose/how-tos/profiles/
   - Relevant contract:
     - `--profile` selectively enables services; suitable for optional test DB services.

10. Docker Compose `--env-file` behavior
    - URL: https://docs.docker.com/compose/how-tos/environment-variables/envvars/
    - Relevant contract:
      - Explicit env-file usage is supported and deterministic.

## Upstream Action Availability Snapshot (Verified)

Verified on 2026-05-02 via GitHub REST API:

- `https://api.github.com/repos/actions/checkout/releases/latest` -> `v6.0.2`
- `https://api.github.com/repos/actions/setup-python/releases/latest` -> `v6.2.0`
- `https://api.github.com/repos/actions/setup-node/releases/latest` -> `v6.4.0`
- `https://api.github.com/repos/astral-sh/setup-uv/releases/latest` -> `v8.1.0`
- `https://api.github.com/repos/gitleaks/gitleaks-action/releases/latest` -> `v2.3.9`

Pinned commit SHAs resolved from release tags on 2026-05-02:

- `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd`
- `actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405`
- `actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e`
- `astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b`
- `gitleaks/gitleaks-action@ff98106e4c7b2bc287b24eaf42907196329070c7`

## Decision

- Implement GitHub CI in `.github/workflows/ci.yml` with:
  - least-privilege token permissions,
  - immutable pinned action SHAs,
  - secret scan gate,
  - backend and frontend gates.
- Preserve container-first execution by making backend quality and integration checks run through existing Docker Compose/`just` runtime patterns instead of host-local Python as default behavior.
- Add Dependabot configuration for `uv`, `npm` (`/client`), and `github-actions`.
- Add PR template and local hook/security artifacts to keep local and remote quality posture aligned.

## Code Impact (Planned)

- New `.github/` workflows and governance files.
- New CI/CD standards and runbook docs.
- New gitleaks and pre-commit config + supporting scripts.
- Documentation index and source registry updates.

## Validation Plan

- Validate YAML structure using local parse checks.
- Validate file presence and references.
- Validate workflow gate intent against existing `justfile` container-first recipes.
- Do not install new runtime dependencies during this rollout.

## Notes / Risks

- Existing `.env.docker` uses machine-specific `DATASET_HOST_PATH`; CI must override it to a repository-local path to avoid host-path failures.
- Frontend currently exposes `lint`, `typecheck`, and `build` scripts; CI should gate those explicitly.
- Action SHAs should be reviewed periodically and refreshed with Dependabot updates.

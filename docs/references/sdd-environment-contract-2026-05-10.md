# SDD Reference - Environment Contract Separation (2026-05-10)

## Scope

Separate local-development and production environment semantics without breaking Docker-first execution.

## Official Sources Consulted

1. Docker Compose - environment variables and interpolation precedence
   - https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/
   - https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/
2. Pydantic Settings (v2) - environment-backed settings and validation
   - https://docs.pydantic.dev/latest/concepts/pydantic_settings/
   - https://docs.pydantic.dev/latest/concepts/validators/
3. GitHub Actions - workflow/env/secrets model
   - https://docs.github.com/actions/security-guides/encrypted-secrets
   - https://docs.github.com/actions/learn-github-actions/variables

## Applied Decisions

- Canonical `APP_ENV` values are `development` and `production`.
- Legacy aliases (`local`, `dev`, `prod`) are accepted and normalized for transition compatibility.
- Unknown `APP_ENV` values fail fast.
- Local Docker defaults remain safe (`MERCADO_PUBLICO_API_ENABLED=false` in `.env.docker`).
- Mercado Publico sync commands explicitly opt in to API usage with inline `-e MERCADO_PUBLICO_API_ENABLED=true`.
- Production sync workflow sets `APP_ENV=production` and injects DB/API secrets from GitHub Actions secrets.

## Why This Split

- Avoids implicit behavior from shared or ambiguous defaults.
- Preserves safe local defaults while keeping operator sync commands deterministic.
- Keeps production safety checks explicit and auditable.

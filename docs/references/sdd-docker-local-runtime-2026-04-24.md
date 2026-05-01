# SDD Reference - Docker Local Runtime (2026-04-24)

## Context

Define a minimal, secure local container runtime for backend-first development (`api` + `db`, optional `db_test`) without requiring host-local Python/PostgreSQL.

## Official Sources Consulted

- Docker Compose startup order (`depends_on` with `service_healthy`):
  - https://docs.docker.com/compose/how-tos/startup-order/
- Docker Compose environment variable interpolation:
  - https://docs.docker.com/compose/environment-variables/
- Docker Compose `env_file`:
  - https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/
- Docker bind mounts:
  - https://docs.docker.com/engine/storage/bind-mounts/
- Docker tmpfs mounts:
  - https://docs.docker.com/engine/storage/tmpfs/

## Decisions

1. Use Compose health checks + `depends_on: condition: service_healthy` so API waits for Postgres readiness.
2. Use service DNS names (`db`, `db_test`) in `DATABASE_URL` values for in-network container access.
3. Publish ports on localhost only (`127.0.0.1`) for local development risk reduction.
4. Run API as non-root and set `no-new-privileges` in Compose.
5. Keep API root filesystem read-only and provide writable `tmpfs` at `/tmp`.
6. Mount host dataset read-only at `/datasets/mercado-publico`.
7. Keep Docker configuration in tracked files (`Dockerfile`, `docker-compose.yml`, `.env.docker`) and wire execution through `just` recipes.

## Addendum 2026-04-30

Current build-hardening work extends the same Docker-first approach to tooling:

1. Use a multi-stage Dockerfile so runtime stays lean while a separate `tools` stage can carry dev dependencies for quality gates and tests.
2. Keep the build context small with `.dockerignore`; Docker only needs the files actually copied into the image.
3. Build Compose services from explicit targets when a Dockerfile contains multiple stages.

## Official Sources Consulted

- Docker multi-stage builds:
  - https://docs.docker.com/build/building/multi-stage/
- Docker build context and `.dockerignore`:
  - https://docs.docker.com/build/concepts/context/
- Compose build specification, including `target`:
  - https://docs.docker.com/compose/compose-file/build/

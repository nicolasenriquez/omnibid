# Local Adaptations for `app-chilecompra`

The assets in `.codex/` were imported from the reference project and kept mostly intact.

For this repository, use these canonical mappings:

- `app/` -> `backend/`
- `frontend/` -> `client/`
- Runtime command -> `just api`
- Fast CI -> `just backend-ci-fast`
- Full CI -> `just backend-ci`
- Bronze canonical pipeline -> `just bronze-load`
- Silver build -> `just silver-load`

When a command document conflicts with this repository, `AGENTS.md` + `RTK.md` + `justfile` are the source of truth.

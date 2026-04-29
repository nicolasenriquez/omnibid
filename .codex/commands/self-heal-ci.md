Run iterative local CI healing until gates pass or a real blocker is reached.

Optional input: `@ARGUMENTS`

Supported call shapes:
- `/self-heal-ci`
- `/self-heal-ci target=fast|full`
- `/self-heal-ci using=back|front|all`
- `/self-heal-ci scope=back|front|all` (alias)
- `/self-heal-ci max=<int>`
- `/self-heal-ci autofix=on|off`
- `/self-heal-ci env_block=stop|continue`
- `/self-heal-ci confirm=high-risk target=full using=all max=5 autofix=on`

Defaults:
- `target=fast`
- `using=back` (`scope=back` alias)
- `max=2`
- `autofix=off`
- `env_block=stop`

## Goal

Converge local CI gates to green using minimal, iterative fixes:
- run the right CI target (`fast` or `full`) on selected scope (`using=back|front|all`)
- detect the first failing gate
- apply only low-risk fixes unless explicitly approved for high-risk mode
- rerun and repeat until pass or blocked

By default this command is diagnose-first and conservative. It can apply non-semantic lint/format fixes when safe. It must not make infrastructure, database, or CI policy changes unless explicitly approved via `confirm=high-risk`.

## Target + Scope Semantics (`using`/`scope`)

`target=fast`:
- `using=back` (`scope=back`) -> `just ci-fast`
- `using=front` (`scope=front`) -> `npm run lint`, `npm run typecheck`, `npm run build` from `client/`
- `using=all` (`scope=all`) -> `just ci-fast`

`target=full`:
- `using=back` (`scope=back`) -> `just ci`
- `using=front` (`scope=front`) -> frontend commands above
- `using=all` (`scope=all`) -> `just ci`

Why conservative defaults:
- reduce accidental broad edits from a repair command
- keep CI healing deterministic and auditable
- preserve human control for high-impact paths

## Guardrails

- Do not run destructive git commands.
- Do not commit or push.
- Do not silence type/lint/security/test failures to force green.
- Keep fixes minimal and localized to failing gates.
- Stop if failure is clearly environmental (DB down, missing tool, network policy, missing secrets).
- If the same failure signature repeats twice with no meaningful progress, stop and report `BLOCKED`.
- `autofix=on` may only apply non-semantic lint/format fixes.
- For `type`, `security`, `test`, or `pre-push` failures: diagnose and propose exact fix commands; do not auto-edit behavior by default.
- Protected paths must not be modified unless the user explicitly sets `confirm=high-risk`:
  - `.github/workflows/**`
  - `alembic/**`
  - `docker-compose.yml`, `Dockerfile`
  - `pyproject.toml`, `justfile`, `.pre-commit-config.yaml`
  - `backend/core/config.py`, `backend/db/session.py`, `backend/db/base.py`
- If a required fix touches protected paths and `confirm=high-risk` is not present, stop and return `BLOCKED` with a human approval request.
- Classify known environment-only blocker signatures explicitly:
  - `PermissionError: [Errno 1] Operation not permitted` from Python multiprocessing `SyncManager` (sandbox/runtime socket bind limitation)
  - DNS/network resolution failures for `pip-audit` (`pypi.org` or registry host resolution)
  - DB connectivity/permission failures while running migration or integration gates
- `env_block=stop` (default): stop at first confirmed environment blocker.
- `env_block=continue`: record blocker and continue remaining gates; finish with `PARTIAL PASS` if no code failures remain.

## Process

### 1) Preflight

Run:

```bash
pwd
git rev-parse --abbrev-ref HEAD
git status --short
```

Check required tools:

```bash
command -v just || true
command -v uv || true
command -v npm || true
```

If `just` is missing, use explicit fallback commands (see step 3 fallback map).

### 2) Iterative healing loop (up to `max`)

For each iteration:

1. Run the selected pipeline for `(target, using/scope)`.
2. If green, finish.
3. If red, isolate first failing gate by running the smallest sequence:

Backend gates:

```bash
just lint
just type
just security
just test-unit
just test-integration
```

Frontend gates:

```bash
cd client
npm run lint
npm run typecheck
npm run build
```

Pre-push hooks (when target includes full `ci`):

```bash
just ci
```

4. Apply smallest safe fix for the first failing gate:
- lint/format failures:
  - if `autofix=on`, run `just format`, then rerun the same gate
  - if `autofix=off`, stop with exact fix commands
- type/security/test/pre-push failures:
  - default mode: stop with diagnosis, affected files, and exact fix commands
  - if `confirm=high-risk`, proceed with minimal fix while respecting protected-path guardrails

5. Rerun only the previously failing gate first, then rerun pipeline phase.

Fallback map when `just` is unavailable:
- backend lint: `uv run ruff check backend tests scripts`
- backend lint fallback if black multiprocessing fails: `uv run black . --check --diff --workers 1`
- backend format: `uv run ruff check backend tests scripts --fix` + `uv run black backend tests scripts`
- backend type: `uv run mypy backend scripts`
- backend security: `uv run bandit -c pyproject.toml -r backend --severity-level high --confidence-level high`
- backend tests: `uv run pytest -q -m "not integration"` and integration through `just test-integration`
- frontend lint/type/build: `cd client && npm run <script>`

When `pip-audit` fails with DNS/network-only errors:
- classify as environment blocker (`failure_type=network`)
- if `env_block=stop`, end with `BLOCKED`
- if `env_block=continue`, continue remaining gates and report `PARTIAL PASS`

### 3) Stop conditions

Return `PASS` when target is fully green.

Return `PARTIAL PASS` when:
- selected scope converges partially but environment-only blockers remain for required gates.

Return `BLOCKED` when:
- environment blockers prevent progress (DB/tool/network/credentials)
- repeated same failure signature with no progress.
- first safe fix requires protected-path edits without `confirm=high-risk`.

Return `FAIL` when:
- iteration limit reached without convergence.

## Output Format

```text
Self-heal CI scope:
- target: fast|full
- using/scope: back|front|all
- max iterations: <n>
- autofix: on|off

Iteration log:
- iter 1: <phase> -> pass/fail -> fix applied: <summary>
- iter 2: <phase> -> pass/fail -> fix applied: <summary>
...

Final gate status:
- selected pipeline: pass/fail/blocked
- overall: PASS | PARTIAL PASS | BLOCKED | FAIL
- blocking_gate: <gate-name or none>
- failure_type: code | env | tooling | network | db
- retryable: yes|no

Files touched:
- <list>

Key blockers or findings:
- <bullets>

Next action:
- PASS -> /commit-local
- PARTIAL PASS or BLOCKED -> exact blocker fix command(s)
- FAIL -> /review-fix (if reviewer findings exist) or focused manual fix plan
```

## Definition of Done

The command is done when:
- selected target reached `PASS`, or
- a concrete `BLOCKED` reason is proven, or
- iteration cap reached with explicit `FAIL` report.

In all cases, output must include:
- what was run
- what was fixed
- what remains
- one exact next command.

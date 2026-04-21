Run validation honestly for the current repository or the current OpenSpec change.

Optional focus: `@ARGUMENTS`

This command should align with the rest of the command layer:

- `/prime` establishes current context
- `/plan` creates an OpenSpec change
- `/execute` implements from that change
- `/validate` proves what actually works now

Use repo reality, not stale expectations.

## Goal

Validate the repo or the active change with the right level of scope, then report:

- what was validated
- what passed
- what failed
- what could not be validated
- what the next action should be

## OpenSpec-aware rule

Validation should first determine whether there is an active or explicitly targeted OpenSpec change.

Run:

```bash
openspec list --json
```

If `@ARGUMENTS` specifies a change name, use that.

If there is one clearly relevant active change, validate in the context of that change.

If there is no active change, run the repository baseline.

If validating a change, inspect it first:

```bash
openspec status --change "<name>" --json
openspec instructions apply --change "<name>" --json
```

Read the relevant context files so the validation report can say whether the implemented work matches the expected scope.

## Validation workflow

### 1. Establish validation scope

Decide whether this is:

- repository baseline validation
- active change validation
- focused subsystem validation if `@ARGUMENTS` indicates one

Always state the scope clearly before running commands.

### 2. Read validation context

Always read:

- `AGENTS.md`
- `README.md`
- `docs/guides/validation-baseline.md`

If validating an OpenSpec change, also read:

- the files listed by `openspec instructions apply --change "<name>" --json`

### 3. Run the repository baseline

Core baseline (preferred):

```bash
just backend-ci
just frontend-ci
```

Equivalent explicit backend gate (if `just` is unavailable):

```bash
uv run ruff check .
uv run black . --check --diff
uv run bandit -c pyproject.toml -r app --severity-level high --confidence-level high
uv run pyright app/
uv run mypy app/
uv run ty check app
uv run pytest -v -m "not integration"
```

### 4. Run environment-dependent checks when relevant

If the work or tests depend on the database, Docker, or server runtime, run the relevant checks too:

```bash
docker-compose up -d db
uv run alembic upgrade head
just test-integration
```

For application runtime checks:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8123 &
curl -s http://localhost:8123/ | python3 -m json.tool
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8123/docs
curl -s http://localhost:8123/health
curl -s http://localhost:8123/health/db
curl -s http://localhost:8123/health/ready
lsof -ti:8123 | xargs kill -9 2>/dev/null || true
```

Only run the checks that are justified by the current scope and environment.

### 5. Interpret results honestly

Do not claim PASS just because linting or typing passed.

A validation report must distinguish between:

- passed
- failed
- blocked by missing environment or service
- not run because out of scope

If a required service like PostgreSQL is not running, say that explicitly.

If a tool reports issues but still exits successfully, include that nuance in the summary.

### 6. Connect the result back to workflow

If validating an OpenSpec change, report whether the change looks:

- ready to continue execution
- blocked and needs a fix
- complete and ready for archive

If validating the repo baseline, report whether the repo is:

- ready for a new `/plan`
- should fix validation drift first
- blocked by environment setup

## Output Format

Use these sections:

### Validation Scope

- repository baseline or change-specific validation
- change name if applicable

### Commands Run

- exact commands executed
- note which commands were skipped and why

### Results

- `ruff`
- `black`
- `bandit`
- `pyright`
- `mypy`
- `ty`
- `pytest`
- integration tests
- runtime checks
- Docker checks

Use `✅`, `❌`, and `⚠️`:

- `✅` passed
- `❌` failed
- `⚠️` blocked, skipped, or partially valid

### Key Findings

- the most important issues or blockers
- concrete evidence, not generic wording

### Overall Assessment

State one of:

- `PASS`
- `PARTIAL PASS`
- `FAIL`
- `BLOCKED`

### Next Action

Recommend the next command or action:

- continue `/execute`
- revise `/plan`
- run `/next-step`
- fix environment
- archive the change

## Guardrails

- Use the real current repo state, not stale test counts or timing assumptions.
- Validation must be scoped intelligently, not blindly maximal every time.
- If a service is required, call it out explicitly.
- Never say all validations passed unless they actually passed.
- Make the report actionable enough that the next command is obvious.

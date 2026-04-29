Execute OpenSpec tasks with task-level control, test-first discipline, and repo-aware validation.

Input: `@ARGUMENTS`

Supported call shapes:
- `/execute <change-name>`
- `/execute <change-name> <task-selector>`
- `/execute <tasks-path>`
- `/execute <tasks-path> <task-selector>`
- `/execute <change-name|tasks-path> [task-selector] preflight=auto|off`
- `/execute <change-name|tasks-path> [task-selector] pf=auto|off`

## Objective

Implement an already-planned OpenSpec change in a controlled way:
- refresh context quickly
- keep scope tight to selected tasks
- honor test-first work when behavior changes
- preserve fail-fast behavior
- preserve and improve task-level traceability with concise notes when useful
- update task checkboxes only when task completion is real
- run smallest useful checks during execution, then broader checks when complete

This command performs code and documentation changes.

## Input Rules

Where:
- `<change-name>` resolves to `openspec/changes/<change-name>/tasks.md`
- `<tasks-path>` points directly to a `tasks.md` file

Optional flags:
- `preflight=auto|off` (default: `auto`)
- `pf=auto|off` (alias)

Normalization:
- if both `preflight` and `pf` are provided, `preflight` wins
- normalize `pf` to `preflight`

If no selector is provided:
- execute the next pending task by default
- if next pending tasks form an obvious top-of-file fail-first cluster, execute the minimal safe bundle

## Task Selector Syntax

Supported selectors:
- single task: `1.1`
- range inside one section: `1.1-1.4`
- mixed list: `1.1,1.3,2.1-2.2`
- whole section: `2`, `2.*`, or `2.x`

Normalization rules:
- remove duplicates
- preserve file order from `tasks.md`
- reject invalid cross-section ranges like `1.1-2.3`

## Guardrails

- Always follow `AGENTS.md` and active change artifacts.
- Use test-first execution when behavior changes.
- Keep scope minimal and task-bound.
- Preserve repository architecture boundaries.
- Preserve fail-fast behavior; do not add hidden production fallbacks.
- Preserve existing task notes; enrich only when high signal.
- Mark task `[x]` only after code/tests/docs/evidence for that task are complete.
- If implementation reveals a real design/scope issue, stop and ask before broadening scope.

## Notes Policy

Use `Notes:` for durable, high-signal context, not diary logs.

Allowed content:
- why task exists
- key constraints/risks discovered
- scope boundary decisions
- important dependency/file path discovered
- evidence pointer useful for future maintainers

Rules:
- keep notes concise
- prefer 1-3 notes per subtask when needed
- place notes immediately below the task checkbox they explain
- use section-level `Notes:` only when the context truly applies to every task in that section
- extend existing note when same idea
- add new note only for distinct new point
- do not paste raw command logs into notes

## Validation Policy

Use two levels:

### A) Task-local proof during execution

Run smallest check proving selected task correctness.

Examples:
- targeted `uv run pytest -v <node-or-path>`
- `uv run ruff check <touched-area>` when practical
- targeted type checks where feasible

### B) Change-complete validation

When target `tasks.md` has no remaining `- [ ]`, run final checks for touched scope:
- specs/docs changed:
  - `openspec validate --specs --all`
- app code touched:
  - `just lint`
  - `just type`
  - `just test-unit`
  - `just security`
  - targeted or broader `uv run pytest -q`
- frontend code touched:
  - from `client/`: `npm run lint`
  - from `client/`: `npm run typecheck`
  - from `client/`: `npm run build`
- db/integration touched:
  - `just docker-start`
  - `just test-integration`

If tasks remain pending:
- report broad validations as deferred
- still run minimal task-local proof for completed work

## Process

### 1) Resolve Target

- if first argument is an existing path ending in `tasks.md`, use it
- else resolve `openspec/changes/<change-name>/tasks.md`
- if unresolved, stop and ask for explicit change name or path

### 2) Preflight Context Refresh

When `preflight=auto`, run a lightweight read-only batch:

```bash
pwd; \
git rev-parse --abbrev-ref HEAD; \
git status --short; \
openspec status --change "<change-name>" --json; \
openspec instructions apply --change "<change-name>" --json
```

Then read:
- `AGENTS.md`
- `README.md`
- `openspec/config.yaml`
- `docs/README.md`
- `docs/runbooks/docker-local.md`
- change `proposal.md`, `design.md`, `tasks.md`, and delta specs from `contextFiles`

If `preflight=off`, report `Preflight: skipped (flag)`.

### 3) Parse and Validate Tasks

- parse checkbox state from `tasks.md`
- parse existing `Notes:` lines for selected tasks when present
- expand selector to concrete task IDs
- if no selector, choose next pending task or minimal fail-first bundle
- ensure selected tasks exist and are pending

### 4) Show Execution Preview

Before coding, show:
- target change/path
- selected tasks
- preflight mode
- run mode (`single`, `sequential`, or `test-first bundle`)

### 5) Execute Selected Tasks

For each task:
- implement only task-required scope
- add/update tests first when behavior changes
- update docs/evidence files when task requires them
- reconcile notes when high-value context appears
- run task-local proof
- mark task complete in `tasks.md`

Pause if:
- task is ambiguous
- broader design issue appears
- repo rule conflicts with artifact
- required dependency/environment is missing for safe completion

### 6) Re-check Remaining Work

Re-read `tasks.md` after updates:
- if pending tasks remain: report broader validation as deferred
- if no pending tasks remain:
  - run final repo-aware validations for touched scope
  - fix and rerun where feasible until green or clearly blocked

## Output Format

### 1) Execution Preview
- target
- selected tasks
- preflight mode
- run mode

### 2) Run Completion
- `Completed:` task IDs finished in this run
- `Summary:` one to three concise bullets
- `Files:` key files added/modified
- `Notes:` preserved/enriched/unchanged
- `Checks:` task-local proof plus whether broader validation was deferred or fully run

### 3) Run Summary
- completed task IDs
- remaining pending task IDs
- files touched
- validation status

### 4) Recommended Next Command
- one concrete next command
- use `/execute <change> <next-selector>` when work remains
- use `/explain <change> <selector>` for walkthrough before next slice
- skill fallback: `$openspec-apply-change`

## Definition of Done

Execution run is complete when:
- target `tasks.md` resolved correctly
- selected tasks executed in valid order
- test-first and fail-fast expectations respected
- notes preserved or enriched appropriately
- completed tasks checked off in `tasks.md`
- task-local proof was run
- broader validation deferred correctly or executed for fully completed change
- concise next-step recommendation provided

Prime the agent with current repository, governance, and OpenSpec runtime context before planning or implementation.

Optional arguments: `@ARGUMENTS`

Supported argument style:
- `scope=app|docs|openspec|all` (default: `all`)
- `mode=quick|full` (default: `full`)
- `change=<change-name>` (optional)

If no arguments are provided, use `scope=all` and `mode=full`.

This command is read-only. Do not modify files.

## Objective

Build an accurate, current understanding of:
- repository rules and delivery expectations
- active OpenSpec change state
- the single best next action right now

## Guardrails

- Do not edit files.
- Do not run destructive git commands.
- Prefer repository docs plus OpenSpec CLI JSON as source of truth.
- Treat valid JSON as authoritative even when stderr/banner text is noisy.
- If required JSON cannot be produced, stop and report the blocker clearly.

## Process

### 0) Preflight

Run a read-only preflight:

```bash
pwd
git rev-parse --abbrev-ref HEAD
git status --short
git log --oneline -10
```

Validate:
- repo root is accessible
- `openspec/` exists
- `openspec/config.yaml` exists

If `openspec/` is missing, recommend `/plan <change description>` and report initialization as blocking.

### 1) Load Governance and Architecture Context

Always read:
- `AGENTS.md`
- `README.md`
- `openspec/config.yaml`

Read based on scope:
- `scope=app|all`:
  - `app/main.py`
  - `app/core/config.py`
  - `app/core/database.py`
  - `app/core/logging.py`
- `scope=docs|all`:
  - `docs/product/prd.md`
  - `docs/product/decisions.md`
  - `docs/guides/validation-baseline.md`
  - `docs/product/roadmap.md`
  - `docs/product/backlog-sprints.md`
- `scope=openspec|all`:
  - current change artifacts selected in Step 2

If `openspec/project.md` exists, treat it as useful legacy context, not the primary source of behavior policy.

### 2) Get Authoritative OpenSpec Runtime State

Run:

```bash
openspec schemas --json
openspec list --json
```

Status rules:
- if `change=<change-name>` is provided:
  - run `openspec status --change "<change-name>" --json`
  - run `openspec instructions apply --change "<change-name>" --json`
- if no change is provided:
  - inspect candidates from `openspec list --json`
  - run `openspec status --change "<name>" --json` for the most relevant active change(s)
  - run `openspec instructions apply --change "<best-candidate>" --json` for the best candidate

Use `openspec instructions proposal --change "<name>" --json` only when artifact diagnosis is needed.

### 3) Routing Logic

Use these rules in order:
1. `new`
- no relevant active change exists
2. `continue`
- artifacts are incomplete or `apply.state` is `blocked`
3. `apply`
- artifacts are complete and apply state is `ready`
4. `verify`
- apply state is `all_done` and the change needs conformance review
5. `archive`
- verification evidence exists and change is closure-ready

Important:
- do not use `status.isComplete` alone to infer implementation completion
- use `openspec instructions apply` state and task progress as runtime truth

### 4) Mode Depth

`mode=full`:
- inspect `.codex/skills/openspec-*/SKILL.md` for lifecycle alignment
- check command-doc drift in `.codex/commands/README.md`
- verify quality gates and docs obligations relevant to the candidate change

`mode=quick`:
- read only essential governance files and OpenSpec JSON
- skip deep skill inspection unless anomalies appear

Auto-escalate `quick` to `full` if confidence drops to `Medium`/`Low` or runtime signals disagree.

### 5) Diagnose Workflow Health

Check for:
- active changes and real task progress
- mismatch between command expectations and artifact/task shape
- missing validation or documentation obligations relevant to current scope

Classify issues as:
- `non-blocking`
- `blocking`

## Output Format

### 1) Snapshot
- repo purpose
- stack
- branch and recent activity

### 2) Rules That Matter
- key constraints from `AGENTS.md`
- quality gates from docs/commands
- documentation obligations that affect next work

### 3) OpenSpec State
- schema(s)
- active changes
- artifact readiness
- apply progress/state for the relevant candidate

### 4) Alignment Check
- whether repo rules and current change state align
- inconsistencies or risks
- `non-blocking` vs `blocking`

### 5) Recommended Next Command
- one exact next command
- why it is the best next move
- one fallback command
- when relevant, include skill fallback:
  - `/plan <change>` -> `$openspec-explore` (for clarification)
  - `/execute <change> [selector]` -> `$openspec-apply-change`
  - archive step -> `$openspec-archive-change`

### 6) Confidence
- `High` | `Medium` | `Low`
- short reason

### 7) Open Questions
- only real blockers or ambiguities requiring user input

## Definition of Done

This command is complete when:
- no files were changed
- governance and OpenSpec runtime were analyzed from repository truth
- routing used `openspec instructions apply` for implementation readiness
- one clear next command was recommended
- confidence and blockers were stated explicitly

# Commands Guide

This folder contains repo-local commands for working effectively in this codebase with Codex.

These commands align with:
- repository rules in `AGENTS.md`
- product and delivery guidance in `docs/`
- the OpenSpec workflow used in this repository

## Recommended Flow

Use these tracks most of the time:

```text
/prime [optional preflight]
/next-proposal
/new-branch feat <short-description>
$openspec-propose "<change-name>"
/plan <change description>
/change-ready [optional focus]         # optional gated wrapper for the four lines above
/next-step                             # optional if you already have an active change and need implementation sequencing
/review-fix [optional findings]
/explain <change-name> <task-selector>   # optional learning/review step
/execute <change-name> [task-selector]
/self-heal-ci [optional target/using]
/validate
/commit-local [optional intent]
/design-review [optional target]             # optional frontend UX/technical quality pass
```

Mental model:
- `/prime` = optional repo/runtime preflight before proposal or implementation work
- `/next-proposal` = recommend the next formal proposal grounded in docs, changelog, git history, and runtime state
- `/new-branch` = create the feature branch before proposal artifacts are written
- `$openspec-propose` = create proposal artifacts on that branch
- `/next-step` = pick the highest-leverage next implementation step
- `/plan` = produce an execution-ready plan from OpenSpec artifacts
- `/change-ready` = optional human-in-the-loop wrapper that stops once the change is ready for `/execute`
- `/review-fix` = convert review findings into a minimal fix plan in `/explain` structure
- `/explain` = explain task slices before coding (read-only)
- `/execute` = implement task slices with explicit validation
- `/design-review` = optional comprehensive frontend UX audit/critique + automated improvement pipeline
- `/self-heal-ci` = iterate minimal fixes until local CI gates converge or a real blocker is confirmed (`target=fast|full`, `using=back|front|all`)
- `/validate` = report what actually passes, fails, or is blocked
- `/commit-local` = create a local commit and stop before push

## OpenSpec Relationship

This repo uses OpenSpec as planning and change-management source of truth.

That means:
- planning artifacts live under `openspec/changes/<change>/`
- execution should run from OpenSpec apply instructions
- validation should account for whether scope is repo-wide or change-specific
- repo-local command docs should invoke OpenSpec through `just openspec ...`, which routes to the Dockerized CLI

You can also use official OpenSpec skills directly when better fit:
- `$openspec-propose`
- `$openspec-apply-change`
- `$openspec-archive-change`
- `$openspec-explore`

## Repository Routing Rules

Current repo paths:

- Backend/API: `backend/`, especially `backend/api/routers/`
- Data pipeline: `backend/ingestion/`, `backend/normalized/`, `scripts/`
- Database schema: `backend/models/` plus `alembic/versions/`
- Frontend: `client/`, especially `client/app/licitaciones/` and `client/src/features/opportunity-workspace/`
- Runtime: Docker-first via `just docker-start`, `just docker-pipeline-full`, `just docker-smoke`
- Documentation: `README.md`, `docs/README.md`, `docs/architecture/`, `docs/runbooks/`

Do not route new work to legacy `app/` or `docs/product/prd.md` paths; those are not current repo structure.

## OpenSpec Artifact Standard

When repo-local commands create, review, or refine OpenSpec artifacts, they should enforce these conventions:

- `proposal.md`: capability lists are explicit and use `None.` when a list is empty
- `design.md`: always includes an `Open Questions` section; use `None.` when nothing is open
- `tasks.md`: task notes are task-local by default and sit immediately below the relevant checkbox
- `tasks.md`: section-level `Notes:` are only for constraints that truly apply to the whole section
- `tasks.md`: prefer concrete executable tasks over broad section-wide commentary

These rules are part of artifact quality, not cosmetic preferences. Commands that prepare a change for `/execute` should treat drift from this standard as an artifact-quality issue.

## Commands

### `/prime`

Use when:
- starting a new session
- returning after context loss
- before planning or implementation

What it does:
- checks repo state and constraints
- checks OpenSpec runtime state (`status` + `apply`)
- reports alignment risks/blockers
- recommends one best next command

Examples:

```text
/prime
/prime scope=docs mode=quick
/prime change=add-pdf-ingestion-without-persistence
```

### `/new-branch`

Use when:
- starting a new change in repos where `main` is PR-only
- you want a single branch-start command that syncs + creates + configures upstream without mandatory push
- you may need to carry a dirty tree into the new branch intentionally (`working_tree=pass`)

What it does:
- verifies you are on local `main` and enforces selected dirty-tree policy
- runs `git fetch origin --prune` + optional `git pull --ff-only origin main` depending on dirty-tree mode
- creates branch with format `<type>/<short-slug>-YYYYMMDD`
- validates ref name and collisions
- configures upstream/tracking for `origin/<same-branch-name>`
- optional publish only when `push=on`
- supports dirty tree modes:
  - `working_tree=pass` (default; carry local dirty tree to new branch)
  - `working_tree=block`
  - `working_tree=stash` (stash, sync, create, pop)

Examples:

```text
/new-branch feat market-data-sync-ops
/new-branch docs yfinance-refresh-runbook
/new-branch type=fix name=adapter-single-column-mismatch
/new-branch fix slug=auto working_tree=pass
```


### `/next-step`

Use when:
- deciding what to build next
- needing a scored recommendation grounded in docs + code

What it does:
- evaluates candidate next steps
- scores top options
- recommends one winner and exact next command

Examples:

```text
/next-step
/next-step pdf pipeline
```

### `/next-proposal`

Use when:
- deciding what proposal should exist next
- wanting a standalone recommendation grounded in docs, changelog, git history, code, and OpenSpec runtime

What it does:
- evaluates top proposal candidates
- checks whether existing active changes should block new proposal work
- recommends one winner plus exact branch, proposal, and planning handoff commands

Examples:

```text
/next-proposal
/next-proposal market data operations
```

### `/change-ready`

Use when:
- you want the repository guided from proposal discovery to plan-ready state with human approval at each major gate
- you expect implementation to be handed to another model after planning is complete

What it does:
- runs proposal discovery
- pauses for human selection
- creates the branch
- creates proposal artifacts
- runs planning
- stops with an implementation handoff for `/execute`

Examples:

```text
/change-ready
/change-ready market data operations
```

### `/plan`

Use when:
- turning an active OpenSpec change into execution-ready implementation planning
- reviewing readiness and quality before coding

What it does:
- reads OpenSpec `status` and `instructions apply`
- runs task quality gate (`Pass | Advisory Gap | Fail`)
- checks design open questions before phased planning
- requires explicit blind-spot analysis and blast-radius diagnosis
- outputs phased execution plan + validation matrix

Examples:

```text
/plan
/plan add-pdf-ingestion-without-persistence
```

### `/explain`

Use when:
- you want task-level implementation understanding before coding
- you want a minimality review for a selected task slice

What it does:
- explains selected task(s) with architecture-aware rationale
- distinguishes planned vs implemented behavior
- can include representative code-shape diffs without editing files

Examples:

```text
/explain add-pdf-ingestion-without-persistence 2.1
/explain openspec/changes/add-pdf-ingestion-without-persistence/tasks.md 2.1-2.3 depth=deep
```

### `/review-fix`

Use when:
- you just ran `/review` and need a minimal, actionable fix plan
- you want `/explain`-structured diagnosis before coding

What it does:
- resolves findings from the latest built-in code-review action context (or explicit input)
- diagnoses root causes and impact per finding
- proposes smallest safe changes aligned with repo rules
- includes rabbit-hole check plus diff/blind-spot analysis

Examples:

```text
/review-fix
/review-fix <paste findings block>
/review-fix <paste findings block> depth=deep
```

### `/execute`

Use when:
- an OpenSpec change is implementation-ready
- you want task-by-task execution with selectors

What it does:
- resolves change or direct `tasks.md` path
- supports selectors like `1.1`, `1.1-1.3`, `2.*`
- supports `preflight=auto|off`
- runs task-local proof first, broader checks on change completion

Examples:

```text
/execute add-pdf-ingestion-without-persistence
/execute add-pdf-ingestion-without-persistence 2.1-2.2
/execute openspec/changes/add-pdf-ingestion-without-persistence/tasks.md 3.* preflight=off
```

### `/design-review`

Use when:
- you want a comprehensive frontend design quality pass before shipping
- you need both UX critique (heuristics, anti-patterns, personas) and technical audit (a11y, perf, responsive, theming)
- you want automated fix sequencing through impeccable skills rather than manual command chaining

What it does:
- runs critique (UX heuristics + deterministic anti-pattern scan) and audit (5-dimension technical quality) as parallel isolated assessments
- synthesizes findings into a unified report with P0-P3 severity rankings
- asks targeted questions tied to specific findings before executing any changes
- auto-executes fix and enhancement commands in dependency order (optimize → harden → clarify → adapt → typeset → layout → colorize → animate → polish)
- ends with before/after score comparison

Examples:

```text
/design-review
/design-review client/app/licitaciones
/design-review client/src/features/opportunity-workspace scope=minimal
/design-review scope=evaluate-only
/design-review preflight=off
```

### `/self-heal-ci`

Use when:
- local `just ci-fast` or `just ci` is red and you want controlled iterative healing
- you want diagnosis-first output with optional low-risk autofix

What it does:
- runs selected CI target (`target=fast|full`) on selected scope (`using=back|front|all`)
- defaults to conservative mode: `target=fast`, `using=back`, `max=2`, `autofix=off`
- isolates first failing gate
- applies only non-semantic lint/format autofix by default
- blocks protected-path and high-impact changes unless explicitly approved (`confirm=high-risk`)
- reruns iteratively up to a max cycle count
- exits as `PASS`, `PARTIAL PASS`, `BLOCKED`, or `FAIL` with concrete next action

Examples:

```text
/self-heal-ci
/self-heal-ci target=fast using=back autofix=on
/self-heal-ci confirm=high-risk target=full using=all max=5 autofix=on
```

### `/validate`

Use when:
- you want baseline validation for repo or active change
- you need clear `PASS | PARTIAL PASS | FAIL | BLOCKED`

What it does:
- establishes validation scope first
- runs only justified checks from the baseline toolchain (`ruff`, `black`, `bandit`, `pyright`, `mypy`, `ty`, `pytest`)
- reports passed/failed/blocked/skipped with evidence

Examples:

```text
/validate
/validate add-pdf-ingestion-without-persistence
```

### `/commit-local`

Use when:
- you want one single local commit but will push manually later
- you want the command to stage the full working tree and stop after commit creation

What it does:
- inspects staged, unstaged, and untracked changes together
- stages the intended full local change with `git add -A`
- proposes a descriptive conventional commit message
- generates a copy-paste-ready PR extended description aligned to `.github/pull_request_template.md` when present
- creates the local commit and stops before push

Examples:

```text
/commit-local
/commit-local finalize docs reorganization
```

## Best Practices

- Run `/prime` when you want an explicit repo/runtime preflight before starting proposal or implementation work.
- Use `/next-proposal` when you want a standalone recommendation for what to formally propose next.
- Create the branch before running `$openspec-propose` so proposal artifacts are created on the feature branch, not `main`.
- Use `/change-ready` when you want a gated 1-to-5 workflow that stops before coding.
- Use `/next-step` when direction is unclear.
- Use `/plan` before `/execute` for non-trivial changes.
- Treat `/plan` as the model-handoff boundary when implementation will be done by a different model.
- Use `/explain` when you want to review a slice before coding it.
- Keep `/execute` runs task-scoped and validation-backed.
- Use `/validate` for reality-based status, not optimistic status.
- Use `/design-review` when you want a comprehensive frontend UX/technical quality pass with automated fix sequencing through impeccable skills.
- Use `/commit-local` when the commit should be created now but pushing will be manual.

## Notes

- Keep command docs aligned with real repo structure and workflow.
- If command behavior changes, update this README in the same change.

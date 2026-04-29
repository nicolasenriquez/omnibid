Build a repository-fit OpenSpec implementation plan before coding.

Input: `@ARGUMENTS` (optional change name)

This command is planning-only. It must not implement production code.

## Objective

Convert approved OpenSpec artifacts into a low-risk implementation plan that respects:
- test-first discipline
- investigation before implementation
- explicit blind-spot analysis before coding
- explicit blast-radius diagnosis before coding
- task-level traceability using concise notes
- fail-fast behavior
- architecture boundaries in this repo
- documentation and validation obligations

## Input

Optional argument:
- `<change-name>`

If no argument is provided:
- run `openspec list --json`
- if only one clearly relevant active change exists, use it
- if multiple active changes are plausible, ask the user to choose

## Guardrails

- Do not modify application code during planning.
- Do not modify OpenSpec artifacts unless the user explicitly asks.
- Use OpenSpec CLI JSON output as source of truth.
- Prefer minimal, incremental work over broad refactors.
- Follow repository architecture and typing rules from `AGENTS.md`.
- Call out fail-fast requirements when external dependencies/config are in scope.
- Include relevant docs and validation obligations explicitly.
- Treat unresolved `Open Questions` in `design.md` as planning-critical inputs.
- Diagnose blast radius explicitly for new routes, configs, contracts, schemas, dependencies, persistence boundaries, and operator workflow.
- Call out likely blind spots explicitly, especially where current changes can propagate risk into later backlog items or future slices.
- Treat `CHANGELOG.md` as a required documentation target whenever the change affects behavior, contracts, workflow, or delivery policy.
- Treat artifact quality as part of planning safety:
  - `proposal.md` capability lists must be explicit and use `None.` when empty
  - `design.md` must include an `Open Questions` section, even if it only says `None.`
  - `tasks.md` should place `Notes:` directly under the task they explain; section-level notes are advisory-only unless truly section-wide

## Task Quality Gate

Evaluate task quality with:
- `Pass`
- `Advisory Gap`
- `Fail`

Checks:
1. Investigation-first structure
- `Pass`: explicit investigation section or equivalent early discovery task
- `Advisory Gap`: no explicit section, but plan is still low-risk
- `Fail`: missing investigation and meaningful unknowns remain
2. Notes on tasks
- `Pass`: tasks include concise, useful notes where needed and task-local notes are attached to the relevant checkbox
- `Advisory Gap`: notes are sparse, overly section-level, or partially detached from the tasks they explain, but plan remains executable
- `Fail`: intent or constraints are ambiguous without notes
3. Test-first intent
- tasks begin with failing or baseline-locking tests when behavior changes
4. Scope discipline
- tasks are grouped into coherent units (`app`, `docs`, `verification`, `infra` as needed)
5. Documentation coverage
- changed behavior/contracts include docs updates where needed
6. Verification coverage
- explicit validation tasks and evidence expectations exist
7. Architecture/governance fit
- artifacts align with strict typing, logging conventions, and repository structure
8. Blind-spot coverage
- `Pass`: artifacts identify likely hidden risks, ambiguities, or downstream contract traps
- `Advisory Gap`: likely blind spots exist but are low-risk and called out during planning
- `Fail`: meaningful blind spots remain unexamined and could invalidate implementation order or contract shape
9. Blast-radius coverage
- `Pass`: affected files, modules, configs, contracts, docs, and future workflow dependencies are called out explicitly
- `Advisory Gap`: impact is mostly understood but one or two edges still need confirmation
- `Fail`: implementation could propagate into adjacent slices or operator workflow without an explicit impact map

If any gate is `Fail`:
- stop planning
- output `Task Refinement Needed`
- list minimum artifact edits required before safe execution

If any gate is `Advisory Gap`:
- planning may continue
- recommend minimum refinements before `/execute`

## Process

### 1) Select the Target Change

Run:

```bash
openspec list --json
```

### 2) Confirm Workflow State

Run:

```bash
openspec status --change "<change-name>" --json
openspec instructions apply --change "<change-name>" --json
```

Use:
- `status` for artifact readiness
- `apply` for implementation progress and pending task inventory

If `apply.state` is `blocked`, stop and recommend completing artifacts first.

### 3) Load Planning Context

Read:
- files from `contextFiles` in `openspec instructions apply`
- `AGENTS.md`
- `README.md`
- `openspec/config.yaml`
- `docs/README.md`
- `docs/runbooks/docker-local.md`
- `docs/runbooks/local_development.md`
- `docs/runbooks/operations.md`
- relevant domain docs (`docs/product/product_vision.md`, `docs/architecture/*.md`) when needed

### 4) Review Design Open Questions

Inspect `design.md` for an `Open Questions` section.

Rules:
- if `design.md` is absent: `Open Questions Review: Pass (no design.md)`
- if section absent: `Open Questions Review: Pass (none listed)`
- if section says none/closed: `Open Questions Review: Pass`
- if unresolved questions exist: `Open Questions Review: Decision Needed`

When unresolved questions exist:
- stop before phased planning
- list one bullet per question with:
  - `Why:`
  - `Affects:`
  - `Recommendation:`
- end with `Planning Paused Pending Design Decisions`

### 5) Run the Task Quality Gate

Apply the quality checks above.

If any gate is `Fail`, stop.

### 6) Diagnose Blast Radius and Blind Spots

Before phased planning, produce an explicit diagnosis covering:
- files/modules likely touched now
- configs, env vars, routes, schemas, and dependencies likely touched now
- contracts or docs that this change can invalidate downstream
- later backlog items or future slices that depend on this contract
- security or trust boundaries introduced by the change
- likely blind spots or ambiguous assumptions that could cause rework

Classify each finding as:
- `blocking`
- `non-blocking`

If a `blocking` blind spot or blast-radius uncertainty exists:
- stop planning
- state the minimum artifact refinement needed before `/execute`

### 7) Build Task Decomposition

Decompose into work units, for example:
- `app`
- `shared`
- `docs`
- `infra`
- `verification`

For each unit identify:
- dependencies
- likely files/modules touched
- risk level: `Low` | `Medium` | `High`

### 8) Build Validation Matrix

Choose smallest commands that still meet repository expectations.

Typical commands:
- OpenSpec/docs:
  - `openspec validate --specs --all`
- App code:
  - `just lint`
  - `just type`
  - `just test-unit`
  - `just security`
  - targeted `uv run pytest -q <path-or-node>`
- Frontend code:
  - from `client/`: `npm run lint`
  - from `client/`: `npm run typecheck`
  - from `client/`: `npm run build`
- Integration/db only when needed:
  - `just docker-start`
  - `just test-integration`

### 9) Build the Phased Plan

For each phase include:
- goal
- tasks covered
- likely touched areas
- risks and mitigations
- exact validation commands
- exit criteria

### 10) Recommend Best Next Action

Usually:
- `/execute <change-name> <first-task-or-bundle>`

Fallbacks:
- `/explain <change-name> <task-selector>` for walkthrough-first
- `$openspec-apply-change` as implementation skill fallback

### 11) Build the Implementation Handoff

End with a concise handoff block that another model or operator can use without rereading the whole plan.

Include:
- resolved `change-name`
- execution readiness: `execute-ready` | `blocked`
- first recommended task selector or bundle
- exact `/execute <change-name> <selector>` command when ready
- blockers or decisions still outstanding
- validation expectations for the first execution slice

## Output Format

### 1) Change Snapshot
- change name
- schema
- apply state
- progress
- implementation readiness

### 2) Design Open Questions Review
- Status: `Pass` | `Decision Needed`
- if `Decision Needed`: list question bullets (`Why`, `Affects`, `Recommendation`) and stop

### 3) Task Quality Gate
- Investigation-first structure: `Pass` | `Advisory Gap` | `Fail`
- Notes on tasks: `Pass` | `Advisory Gap` | `Fail`
- Test-first intent: `Pass` | `Advisory Gap` | `Fail`
- Documentation coverage: `Pass` | `Advisory Gap` | `Fail`
- Verification coverage: `Pass` | `Advisory Gap` | `Fail`
- Architecture/governance fit: `Pass` | `Advisory Gap` | `Fail`
- Blind-spot coverage: `Pass` | `Advisory Gap` | `Fail`
- Blast-radius coverage: `Pass` | `Advisory Gap` | `Fail`

### 4) Blast Radius and Blind Spots
- current-slice impact map
- downstream impact map
- `blocking` vs `non-blocking`
- minimum refinements required before `/execute` when blocking issues exist

### 5) Task Decomposition
- ordered work units
- dependencies
- risk level per unit

### 6) Phased Plan
- one phase at a time with goal, touched areas, validations, exit criteria

### 7) Validation Matrix
- exact commands
- when to run them
- expected evidence

### 8) Documentation Checklist
- docs to update for changed behavior/contracts

### 9) Implementation Handoff
- change name
- readiness: `execute-ready` | `blocked`
- first recommended selector
- exact `/execute` command
- blockers or open questions
- first-slice validation expectations
- whether `CHANGELOG.md` must be updated now
- spec/delta alignment checks as relevant

### 9) Recommended Next Command
- one exact next command
- one fallback command

### 10) Confidence
- `High` | `Medium` | `Low`
- short reason

### 11) Open Questions
- only blockers requiring user input

## Definition of Done

Planning is complete when:
- one target change is selected
- artifact readiness and apply progress were both checked
- design open questions were reviewed before phased planning
- unresolved design questions pause planning
- quality gate status is explicit
- blind spots and blast radius were diagnosed explicitly
- phased execution + validation are explicit
- documentation obligations explicitly include whether `CHANGELOG.md` must change
- one clear next command is recommended

Recommend the best next proposal for this repository without making code changes.

Optional focus: `@ARGUMENTS`

This command is a repo-local proposal discovery helper. It is designed to work well as a standalone `/next-proposal` command with no extra context.

Use it when the user wants help deciding:

- what proposal should exist next
- which roadmap or backlog item is the best next formal change
- whether there is unfinished active-change work that should block a new proposal
- which proposal is the best next fit for the current codebase, docs, and recent delivery history

Do not create OpenSpec artifacts and do not implement code during `/next-proposal`.

## Goal

Read the current codebase, source-of-truth docs, changelog, and OpenSpec runtime, then recommend the highest-leverage next proposal that is:

- aligned with the documented MVP and current phase
- justified by recent implementation history
- scoped tightly enough to propose cleanly
- ready for `$openspec-propose` without avoidable ambiguity

## Workflow

### 1. Inspect current repo and workflow state

Run:

```bash
git status --short --branch
git log -10 --oneline
openspec list --json
openspec schemas --json
```

Use this to identify:

- branch and dirty state
- recent implementation focus
- whether there are active OpenSpec changes already
- whether proposal discovery should pause because an in-flight change needs continuation instead

### 2. Read source-of-truth product and delivery docs

Read:

- `AGENTS.md`
- `README.md`
- `CHANGELOG.md`
- `docs/README.md`
- `docs/product/product_vision.md`
- `docs/architecture/system_architecture.md`
- `docs/architecture/data_architecture.md`
- `docs/architecture/data_model.md`
- `docs/runbooks/docker-local.md`
- `docs/runbooks/local_development.md`
- `docs/runbooks/operations.md`
- `docs/references/sdd-official-sources-registry.md`
- `openspec/config.yaml`
- `openspec/project.md` if it exists

If `@ARGUMENTS` is focused on a subsystem, also read the most relevant reference guides or implementation files for that area.

### 3. Ground the recommendation in the actual codebase

Read the core implementation files that define the current system shape:

- `backend/main.py`
- `backend/core/config.py`
- `backend/db/session.py`
- `backend/observability/logging.py`
- `backend/api/routers/`
- `client/package.json`
- `client/app/licitaciones/page.tsx`

If needed, inspect tests, routes, or feature-adjacent files to judge whether a candidate proposal is truly localized and whether prerequisites are already satisfied.

### 4. Deep-check OpenSpec runtime before recommending new work

If `openspec list --json` shows active or ambiguous candidates, inspect the most relevant ones with:

```bash
openspec status --change "<name>" --json
openspec instructions apply --change "<name>" --json
```

Rules:

- if an active change is incomplete and still the highest-leverage path, recommend continuing it instead of proposing new work
- if existing changes are complete or clearly not the right current focus, continue to proposal discovery
- do not rely on change completion status alone; use `instructions apply` runtime state when available

### 5. Evaluate candidate proposals

Generate the top 3 next proposal candidates based on:

- roadmap and backlog priority
- recent implementation and documentation history
- explicit follow-up notes in `CHANGELOG.md`
- current codebase readiness
- validation and operational readiness
- proposal locality and implementation tractability

For each candidate, score it from `1-10`.

The score should represent:

- product relevance now
- clarity of scope
- readiness to propose now
- implementation locality
- fit with the current delivery sequence

### 6. Recommend one winner

Choose exactly one proposal and explain:

- why it is the best next move now
- which concrete repository signals support it
- why it is better than the other two candidates
- whether any prerequisite investigation should be called out inside the proposal
- what the normalized change name and branch slug should be

### 7. Prepare the branch-first handoff

For a new proposal winner, derive:

- `recommended_change_name`: kebab-case OpenSpec change name
- `recommended_branch_slug`: short kebab-case branch slug aligned to the change

Then recommend the branch-first handoff in this order:

```text
/new-branch feat <recommended-branch-slug>
$openspec-propose "<recommended-change-name>"
/plan <recommended-change-name>
```

Important:

- prefer creating the branch before `$openspec-propose` so proposal artifacts are created on the feature branch instead of `main`
- do not assume `/new-branch slug=auto` is reliable here; prefer emitting an explicit branch slug

### 8. End with the next command to run

Finish by recommending the exact immediate next command:

- usually:

```text
/new-branch feat <recommended-branch-slug>
```

- if an active change should be continued first:

```text
/plan <change-name>
```

or

```text
/execute <change-name>
```

depending on runtime state

## Output Format

Return these sections:

### Current State

- concise repo summary
- current workflow state
- recent delivery focus
- active blockers or readiness notes

### Top Candidate Proposals

For each of the top 3:

- name
- score `/10`
- why it is strong or weak now
- key signals from docs, changelog, git history, or codebase reality

### Recommended Proposal

- single winner
- why it wins now
- recommended change name
- recommended branch slug
- likely scope boundaries
- likely artifacts or areas affected

### Why Not The Others

- one concise reason per non-winning candidate

### Handoff Commands

- exact `/new-branch` command
- exact `$openspec-propose` command
- exact `/plan` command

### Recommended Next Command

- exact command text

## Guardrails

- Stay inside the documented MVP unless the user explicitly wants roadmap expansion.
- Prefer proposing the next coherent change over vague strategic brainstorming.
- Ground every recommendation in docs, changelog, recent commits, and current codebase reality.
- Do not auto-create an OpenSpec change.
- Do not recommend a new proposal when an existing active change clearly should be continued first.
- Treat `CHANGELOG.md` as canonical delivery history, not optional context.
- Emit explicit `change_name` and branch slug so the human can execute the next gate without re-deriving names.

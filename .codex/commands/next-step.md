Recommend the best next implementation step for this repository without making code changes.

Optional focus: `@ARGUMENTS`

This command is a repo-local decision helper. It sits between `/prime` and `/plan`.

Use it when the user wants help deciding:

- what to build next
- which backlog item is the best local next step
- which step is best for testing the command system
- whether the repo is ready for planning or should first address validation or workflow gaps

Do not create OpenSpec artifacts and do not implement code during `/next-step`.

## Goal

Read the current codebase and source-of-truth docs, then recommend the highest-leverage next step that is:

- aligned with the MVP
- localized enough to implement safely
- meaningful enough to move the product forward
- good for exercising the repo's command workflow

## Workflow

### 1. Inspect current repo and workflow state

Run:

```bash
git status --short --branch
git log -10 --oneline
openspec list --json
```

Use this to identify:

- branch and dirty state
- recent implementation focus
- whether there are active OpenSpec changes already

### 2. Read source-of-truth product and delivery docs

Read:

- `AGENTS.md`
- `README.md`
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

If needed, inspect tests or feature-adjacent files to judge whether a candidate step is truly localized.

### 4. Evaluate candidate next steps

Generate the top 3 next implementation candidates based on:

- roadmap and backlog priority
- current codebase readiness
- validation readiness
- implementation locality
- suitability for the command workflow

For each candidate, score it from `1-10`.

The score should represent:

- product relevance
- implementation locality
- readiness to plan now
- suitability as a first or next end-to-end command workflow trial

### 5. Recommend one winner

Choose exactly one next step and explain:

- why it is the best next move now
- why it is a good test of `/plan`, `/execute`, and `/validate`
- why it is better than the other two candidates

### 6. End with the next command to run

Finish by recommending the exact next command, typically:

```text
/plan <recommended change description>
```

If the repo is not ready for planning, recommend the correct prerequisite instead.

## Output Format

Return these sections:

### Current State

- concise repo summary
- current workflow state
- active blockers or readiness notes

### Top Candidate Steps

For each of the top 3:

- name
- score `/10`
- why it is a strong or weak next step

### Recommended Next Step

- single winner
- why it wins now

### Why This Is A Good Command-System Test

- how it exercises `/prime`
- how it exercises `/plan`
- how it exercises `/execute`
- what `/validate` should prove afterward

### Next Command To Run

- exact recommended command text

## Guardrails

- Stay inside the documented MVP unless the user explicitly wants roadmap expansion.
- Prefer localized, testable work over broad architectural ambition.
- Ground every recommendation in both docs and current codebase reality.
- Do not auto-create an OpenSpec change.
- Do not recommend a step that clearly depends on missing prerequisite work unless you call that out explicitly.

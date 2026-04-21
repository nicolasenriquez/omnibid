Drive a human-in-the-loop workflow from proposal discovery to implementation-ready planning, stopping before code changes.

Optional focus: `@ARGUMENTS`

This command is a thin orchestrator. It should reuse the logic and standards of the standalone commands instead of inventing a parallel workflow.

Use it when:

- you want a guided gate-by-gate workflow for selecting and preparing the next change
- you want the repository to reach a clean implementation-ready state before handing work to another model or starting `/execute`
- you want explicit human approval between major workflow gates

This command is planning-only. It must not implement production code.

## Goal

Get the repository to a `change-ready` state by guiding this sequence:

1. recommend the best next proposal
2. let the human select the winner
3. create the branch for that winner
4. create OpenSpec proposal artifacts on that branch
5. run `/plan` for the change
6. stop with an implementation handoff for `/execute`

## Workflow

### 1. Proposal Discovery

Run the equivalent of `/next-proposal`.

Requirements:

- read docs, roadmap, backlog, changelog, recent git history, codebase state, and OpenSpec runtime
- generate the top 3 candidate proposals
- recommend one winner
- emit:
  - `recommended_change_name`
  - `recommended_branch_slug`
  - exact `/new-branch` command
  - exact `$openspec-propose` command
  - exact `/plan` command

If an active change should be continued instead of proposing new work:

- stop the workflow
- recommend `/plan <change-name>` or `/execute <change-name>`
- report `Workflow Result: continue-existing-change`

### 2. Human Selection Gate

Present the top candidates and stop for the human to confirm the winner.

Rules:

- do not auto-select a non-trivial proposal without giving the human a clear approval point
- if the human chooses a non-winning candidate, continue using the human's choice

### 3. Branch Creation Gate

Use the equivalent of `/new-branch` with the explicit recommended slug.

Preferred command shape:

```text
/new-branch feat <recommended-branch-slug>
```

Rules:

- branch creation happens before `$openspec-propose`
- if branch creation fails, stop and report the exact blocker
- do not use `slug=auto` unless the human explicitly requests it

### 4. Proposal Creation Gate

Use the `openspec-propose` skill with the selected `change_name`.

Preferred command shape:

```text
$openspec-propose "<recommended-change-name>"
```

Rules:

- create proposal artifacts only after the branch exists
- if a change with that name already exists, stop for human resolution
- after proposal creation, confirm the change path and readiness status
- before moving to `/plan`, verify proposal artifacts follow the repo's OpenSpec artifact standard:
  - `proposal.md` capabilities are explicit and use `None.` when a new/modified capability list is empty
  - `tasks.md` notes are task-local by default and appear immediately after the relevant checkbox
  - section-level `Notes:` are allowed only when they truly apply to the whole section
  - `design.md` includes an explicit `Open Questions` section and says `None.` when there are no open questions

### 5. Planning Gate

Run the equivalent of:

```text
/plan <change-name>
```

Requirements:

- keep planning read-only with respect to application code
- produce task quality gate results
- diagnose blast radius and blind spots
- end with the standardized implementation handoff block

### 6. Stop At Change-Ready

Do not run `/execute`.

Finish only when one of these states is true:

- `change-ready`: proposal artifacts created, branch created, plan completed, implementation handoff available
- `blocked`: a human decision or repo/runtime blocker prevents safe progress
- `continue-existing-change`: active change should be resumed instead of preparing a new one

## Output Format

### Workflow Result

- `change-ready` | `blocked` | `continue-existing-change`

### Selected Change

- change name
- branch name
- why this was selected

### Workflow Commands

```text
/new-branch feat <recommended-branch-slug>
$openspec-propose "<recommended-change-name>"
/plan <change-name>
```

### Gates Completed

- proposal discovery: completed | blocked | not-run
- human selection: completed | blocked | not-run
- branch creation: completed | blocked | not-run
- proposal creation: completed | blocked | not-run
- planning: completed | blocked | not-run

### Implementation Handoff

- change name
- readiness: `execute-ready` | `blocked`
- first recommended selector
- blockers or open questions
- first-slice validation expectations
```text
/execute <change-name> [selector]
```

### Next Action

```text
<one exact next command>
```

## Guardrails

- Reuse the standalone command logic; do not invent a separate policy layer.
- Keep the human in the loop at each major gate.
- Do not create proposal artifacts on `main` when branch creation is feasible first.
- Stop before implementation; `/execute` belongs to the implementation phase and may be handed to another model.
- If the workflow reveals design ambiguity or artifact quality problems, stop and report them instead of forcing progress.

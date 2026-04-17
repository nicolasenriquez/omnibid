Explain OpenSpec tasks in a practical mentor style, with minimality checks and representative code-shape guidance.

Input: `@ARGUMENTS`

Supported call shapes:
- `/explain <change-name>`
- `/explain <change-name> <task-selector>`
- `/explain <change-name> task <task-selector>`
- `/explain <tasks-path>`
- `/explain <tasks-path> <task-selector>`
- `/explain <tasks-path> task <task-selector>`
- `/explain <change-name|tasks-path> [task-selector] audience=junior|intermediate|senior`
- `/explain <change-name|tasks-path> [task-selector] depth=concise|standard|deep`
- `/explain <change-name|tasks-path> [task-selector] code=on|off`
- `/explain <change-name|tasks-path> [task-selector] preflight=off|auto`
- `/explain <change-name|tasks-path> [task-selector] pf=off|auto`

Defaults:
- `audience=junior`
- `depth=standard`
- `code=on`
- `preflight=off`

If no selector is provided:
- explain next pending task by default
- if next pending tasks form a clear fail-first cluster, explain that cluster together

This command is read-only.

## Objective

Explain selected OpenSpec tasks in an implementation-oriented way:
- assess whether selected tasks are minimal for current scope
- explain what changes and why
- connect work to repository rules and architecture
- provide representative code shape without editing code

## Task Selector Syntax

Supported selectors:
- single task: `1.1`
- range inside one section: `1.1-1.4`
- mixed list: `1.1,1.3,2.1-2.2`
- whole section: `2`, `2.*`, or `2.x`

Normalization:
- remove duplicates
- preserve file order from `tasks.md`
- reject invalid cross-section ranges

## Guardrails

- Read-only only: do not edit code/docs/changelogs/tasks.
- Do not mark tasks complete.
- Do not run heavy validation commands.
- Distinguish planned work from already implemented behavior.
- If evidence is incomplete, say so and lower confidence.
- Keep explanation practical and concrete.

## Minimality Rubric

A task set is `minimal` when it is the smallest change that still preserves:
- intended product requirement impact
- required test coverage
- fail-fast behavior
- architecture boundaries
- required docs/evidence for scope

A task set is `partially minimal` when:
- direction is correct but essential work is mixed with optional cleanup

A task set is `not minimal` when:
- scope broadens beyond requirement
- unrelated refactors are mixed in
- extra architecture movement is introduced without artifact support

## Process

### 1) Resolve Target

- if first argument is valid `tasks.md` path, use it
- else resolve `openspec/changes/<change-name>/tasks.md`
- if unresolved, stop and ask for explicit path or change name

### 2) Optional Preflight

Run preflight only when `preflight=auto`.

For a change name:

```bash
pwd; \
git rev-parse --abbrev-ref HEAD; \
git status --short; \
openspec status --change "<change-name>" --json; \
openspec instructions apply --change "<change-name>" --json
```

For a direct path:

```bash
pwd; \
git rev-parse --abbrev-ref HEAD; \
git status --short
```

If `preflight=off`, report `Preflight: skipped (flag/default)`.

### 3) Parse and Validate Tasks

- parse checkbox state and task IDs from `tasks.md`
- expand selector
- if omitted, choose next pending task or minimal test-first cluster

### 4) Gather Evidence

Read:
- `proposal.md`
- `design.md` when present
- delta specs under `specs/**/*.md`
- relevant code files referenced by tasks
- `AGENTS.md` when needed for rationale

Map each task to:
- expected file/area changes
- behavior and contract impact
- architecture/fail-fast implications
- likely test focus

### 5) Generate Explanation

For selected tasks:
- answer minimality directly
- explain what changes and why
- include representative code shape when `code=on`
- tailor detail to `audience` and `depth`

## Output Format

### 1) Direct Minimality Answer
- one direct sentence:
  - `Yes, tasks <selector> are minimal ...`
  - `Partially, tasks <selector> are mostly minimal ...`
  - `No, tasks <selector> are not minimal ...`

### 2) Why This Is Minimal (or Not)
- short numbered points
- include touched runtime files/areas

### 3) Task `<selector>` Explained
For each selected task:
- `Change in <file(s)>:`
- concise bullets of what changes
- `Why needed:` one concise rationale
- `Repository impact:` architecture/tests/docs implications as relevant

### 4) Code-Level Shape (Representative, Not Applied)
Include only when `code=on`.

Format:

`[<task-id>] ->`

`Current (as-is)`

`----------------`

`Plan (to-be)`

`------------`

Optional:

`Removed from Current`

Use markers:
- `+` added lines
- `~` modified lines
- `-` removed lines

### 5) Senior-Level Takeaway
- one concise paragraph stating the key engineering principle from this task set

## Definition of Done

This command is complete when:
- target `tasks.md` resolved and parsed
- selected tasks explained with minimality reasoning
- rationale tied to repository rules where relevant
- code shape provided when enabled
- no files modified

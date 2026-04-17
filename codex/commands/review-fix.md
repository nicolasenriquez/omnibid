Convert latest `/review` findings into a minimal-fix plan using `/explain` structure, without modifying files.

Input: `@ARGUMENTS`

Supported call shapes:
- `/review-fix`
- `/review-fix <findings-text>`
- `/review-fix <findings-text> depth=concise|standard|deep`
- `/review-fix <findings-text> mode=read-only|patch-ready`

Defaults:
- `depth=standard`
- `mode=read-only`

When no findings text is provided:
- use the latest review findings from current conversation context
- prefer findings pasted below a `--------` separator in the most recent user message
- otherwise use the latest structured code-review result block from the built-in review action
  (`<user_action><action>review</action><results>...</results></user_action>`)

If no findings can be resolved, stop and ask the user to paste the findings.

Review-source intent:
- `/review` in this command means the built-in OpenAI/Codex code-review action output
- primary parse target is the `Full review comments:` section
- if no `Full review comments:` block exists but review states no issues, return a no-fix-needed
  response instead of forcing a fix plan

## Objective

Produce a practical, minimal, and codebase-aligned fix proposal from review findings:
- identify root cause per finding
- define smallest safe change set
- avoid scope creep and unrelated refactors
- report rabbit-hole risk explicitly
- reference current diff context and potential blind spots

This command is read-only by default.

## Input Rules

- If findings are passed via `@ARGUMENTS`, treat them as source of truth.
- If no findings are passed, resolve from latest review context as described above.
- Parse each finding with:
  - severity (`P0`/`P1`/`P2`/...)
  - file path and line hint
  - expected behavior and observed risk

Optional flags:
- `depth=concise|standard|deep`
- `mode=read-only|patch-ready`

Normalization:
- if same finding appears multiple times, deduplicate by `file + line + summary`
- preserve source order after deduplication

## Guardrails

- Do not edit files when `mode=read-only`.
- Do not mark tasks complete.
- Do not run destructive git commands.
- Keep recommendations minimal and task-scoped.
- Follow repository rules in `AGENTS.md` (strict typing, fail-fast, architecture boundaries).
- Treat hard quality gates as blocking (mypy/pyright/ruff/tests when applicable).
- If finding appears already fixed in current tree, state that explicitly with evidence.

## Process

### 1) Resolve Findings Source

- Resolve explicit findings input or infer latest review findings from context.
- Prefer latest built-in review action output over free-form historical text when both exist.
- Parse findings from common review structures:
  - `Full review comments:`
  - bullet findings like `- [P1] ...`
  - path and line hints like `— /abs/path/file.py:123-123`
- If unresolved, stop with one clear ask: paste review findings block.

### 2) Gather Minimal Evidence

Read-only checks:

```bash
pwd
git rev-parse --abbrev-ref HEAD
git status --short
```

For each referenced file:
- inspect nearby code region
- inspect current `git diff` for that file
- if file is untracked and diff is empty, report that blind spot explicitly

### 3) Diagnose Per Finding

For each finding:
- what is failing now
- why it fails (root cause)
- user-visible/system impact if not fixed
- smallest safe fix that respects repository constraints
- validation scope needed to prove the fix

### 4) Rabbit-Hole Check

Classify the combined fix as:
- `No rabbit hole`: small localized change
- `Low risk expansion`: small additional adjustments required
- `Potential rabbit hole`: change likely requires broader redesign

State why.

### 5) Build Response in `/explain` Format

Output must include:
- direct minimal-fix answer
- cause and importance
- minimal patch plan per finding
- blind spots and assumptions
- validation checklist

If `mode=patch-ready`, include a short “apply order” section that can be executed next.

## Output Format (`/explain`)

### 1) Minimal Fix Answer
- one direct sentence on whether a minimal fix exists

### 2) Why This Is Happening
- root cause bullets per finding

### 3) Why It Matters
- concrete risk/impact bullets per finding

### 4) Minimal Fix Plan
- per finding:
  - file(s)
  - exact narrow change
  - why this is the smallest safe fix

### 5) Rabbit-Hole Check
- `No rabbit hole` | `Low risk expansion` | `Potential rabbit hole`
- one short rationale

### 6) Diff/Blindspot Review
- what current diff confirms
- what cannot be confirmed (untracked/stale/ambiguous)

### 7) Validation Plan
- smallest command set to prove the fix

## Definition of Done

This command is complete when:
- findings source is explicit or reliably inferred
- each finding has root cause + minimal fix + validation
- rabbit-hole risk is stated
- diff/blindspot analysis is explicit
- no files are modified in `read-only` mode

Create clean commit(s) from the current work and push once to `origin main`.

Optional input: `@ARGUMENTS`

Use this command as the final delivery step after implementation and validation.

Human approval is mandatory:

- before creating each commit
- before the final push to `origin main`

## Goal

Package the intended work into one or more atomic commits for one goal, generate clear and descriptive commit messages from the real diff plus user intent, then push once to `origin main`.

## Input Rule

- Treat `@ARGUMENTS` as extra intent, not as the only source of truth.
- The real source of truth for the commit message is:
  - `git status --short --branch`
  - `git status --porcelain`
  - `git diff HEAD`
- If the input and the diff disagree, trust the diff and report the mismatch.

## Workflow

### 1. Inspect repo state first

Run:

```bash
git status --short --branch
git status --porcelain
git diff HEAD
```

If there are no changes, stop and report that there is nothing to commit.

### 2. Inspect recent history for style continuity

Run:

```bash
git log -10 --oneline
```

Use this only to keep commit style consistent. Do not copy old messages blindly.

### 3. Check whether an OpenSpec change is relevant

Run:

```bash
openspec list --json
```

If there is an active change that clearly matches the current diff, use it as additional context for the commit message and summary.

### 4. Decide whether the work is commit-ready

Before committing, verify:

- the changes form one coherent unit
- unrelated files are not mixed into the commit
- the branch is `main`
- the remote `origin` exists
- validation status is known for risky code changes

If the diff is mixed but still part of one goal, split it into 2-3 coherent commit groups and process them in sequence.

If the diff is mixed and not one goal, stop and explain what should be split out first.

### 5. Stage the intended files

Stage only the files that belong to the atomic change.

Do not silently include unrelated dirty files.

### 6. Generate the commit message

Create a descriptive conventional commit message grounded in the actual diff.

Use a prefix such as:

- `feat`
- `fix`
- `docs`
- `chore`
- `refactor`
- `test`

Rules:

- subject line must be concise and specific
- add a body when it improves clarity
- mention the main behavioral outcome, not just touched files
- use `@ARGUMENTS` only to improve naming and specificity

### 7. Create the commit

Create the commit only after staging and message generation are complete.

Before running the actual `git commit`, show:

- the files that will be included
- the final commit message
- a short summary of the change

Then explicitly ask for human approval.

Do not create the commit until approval is granted.

### 8. Push once after all commit groups are complete

After each successful commit, decide whether more commit groups are still pending for the same goal.

If more groups are pending:

- keep committing group by group
- do not push yet
- report push status as deferred

When the final group is committed, prepare to run:

```bash
git push origin main
```

Before running the final push, explicitly ask for human approval again.

Do not push automatically just because a commit was approved.

If push fails, report the failure clearly and include the reason.

### 9. Report back clearly

Return:

- branch name
- files included in the commit
- final commit message
- commit hash
- push target: `origin main`
- whether push is deferred or succeeded

## Safeguards

- Refuse to continue if there are no changes.
- Refuse to continue if `origin` does not exist.
- Refuse to continue if the current branch is not `main`.
- Refuse to create the commit until human approval is given.
- Refuse to push until a second human approval is given.
- Refuse to push while additional commit groups are still pending for the same goal.
- Warn if validation was not run for code changes that affect runtime behavior.
- Stop if the diff appears to contain unrelated work that should be split into separate commits.

## Output Format

Use this structure:

```text
Commit readiness:
- ready / blocked

Commit summary:
- <high-level summary>

Commit message:
- <final subject>
- <final body if any>

Push result:
- target: origin main
- status: pending approval / deferred / succeeded / failed

Next action:
- <if blocked or failed, say exactly what to do next>
```

## Guardrails

- Do not invent a commit message without reading the diff.
- Do not claim validation passed unless it was actually run.
- Do not create the commit without explicit human approval.
- Do not push if commit creation failed.
- Do not push without explicit human approval, even if the commit already exists.
- Do not push until all planned commit groups for the goal are committed.
- Do not hide mixed or unrelated changes.
- Prefer one clean commit over one noisy commit.

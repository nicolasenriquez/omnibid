Create a new local branch from `main` with standardized naming, optional dirty-tree handling, and upstream tracking preconfigured to `origin/<same-branch-name>`.

Input: `@ARGUMENTS`

Supported call shapes:
- `/new-branch <type> <short-description>`
- `/new-branch type=<type> name=<short-description>`
- `/new-branch <type> [name=<short-description>] [working_tree=block|pass|stash] [working_git=block|pass|stash] [date=YYYYMMDD] [push=off|on]`
- `/new-branch <type> slug=auto [working_tree=pass]`

Defaults:
- `working_tree=pass`
- `date=today` (`YYYYMMDD`, local timezone)
- `push=off`

Examples:
- `/new-branch feat market-data-sync-ops`
- `/new-branch docs yfinance-refresh-runbook`
- `/new-branch feat market-data-scheduler-runbook`
- `/new-branch fix slug=auto working_tree=pass`
- `/new-branch feat portfolio-summary-cards working_tree=stash`

## Objective

Create a reproducible branch-start workflow for PR-only `main` repos:
- verify local safety conditions
- sync from `origin/main` when safe
- create branch name with deterministic convention
- optionally keep dirty working tree and carry it into the new branch
- preconfigure upstream tracking metadata to `origin/<same-branch-name>` without requiring immediate push

## Naming Convention

Branch format:

`<type>/<short-slug>-<YYYYMMDD>`

Allowed `type` values:
- `feat`
- `fix`
- `docs`
- `chore`
- `refactor`
- `test`
- `perf`
- `ci`
- `build`

Slug rules:
- lowercase
- short and descriptive
- kebab-case words
- only `a-z`, `0-9`, and `-`

## Dirty Tree Modes

`working_tree=block`:
- requires clean working tree
- stops if staged/unstaged/untracked changes exist

`working_tree=pass` (default):
- keeps current dirty tree as-is
- creates/switches to the new branch and carries all local changes to it
- runs `fetch` only (no `pull --ff-only`) to avoid unsafe auto-merge with local dirty state

`working_tree=stash`:
- stashes dirty tree (`git stash -u`)
- syncs `main` (`fetch + pull --ff-only`)
- creates new branch
- reapplies stashed changes (`stash pop`)

Alias:
- `working_git=...` is accepted as alias for `working_tree=...`
- if both are provided, `working_tree` takes precedence

## Slug Auto Mode (`slug=auto`)

When `name` is omitted or `slug=auto` is set, derive slug from current implementation context:
1. if there is an active relevant OpenSpec change, derive from change id
2. otherwise inspect `git diff --name-only` + untracked files and map dominant scope
3. normalize to kebab-case and trim to practical length
4. if confidence is low (mixed scope), stop and ask for explicit short description

## Workflow

### 1) Preflight checks

Run:

```bash
pwd
git rev-parse --abbrev-ref HEAD
git status --short
git remote -v
```

Rules:
- current branch must be `main`
- remote `origin` must exist
- dirty-tree policy must be satisfied for selected `working_tree` mode

### 2) Sync `main` safely

Always run:

```bash
git fetch origin --prune
```

Then:
- `working_tree=block` or clean tree:
  - `git pull --ff-only origin main`
- `working_tree=pass` with dirty tree (default behavior):
  - skip `pull` and report that branch starts from current local `main` snapshot
- `working_tree=stash`:
  - stash first, then `git pull --ff-only origin main`

### 3) Build and validate branch name

Build:
- `date_part` from `date +%Y%m%d` unless explicit `date=...`
- slug from explicit name or auto mode
- final `<type>/<slug>-<date_part>`

Validate:

```bash
git check-ref-format --branch "<branch-name>"
git show-ref --verify --quiet "refs/heads/<branch-name>"
git ls-remote --exit-code --heads origin "<branch-name>"
```

Stop if branch name is invalid or exists locally/remotely.

### 4) Create and switch branch

Run:

```bash
git switch -c "<branch-name>"
```

### 5) Configure upstream tracking metadata

Run:

```bash
git config "branch.<branch-name>.remote" origin
git config "branch.<branch-name>.merge" "refs/heads/<branch-name>"
```

### 6) Optional publish (`push=on`)

Run only if requested:

```bash
git push origin "<branch-name>"
```

## Output Format

```text
New branch result:
- status: created / blocked / failed
- base branch: main
- dirty mode: block / pass / stash
- sync: fetched / fetched+ff-pulled / fetched+stash+ff-pulled
- new branch: <branch-name>
- upstream: origin/<branch-name> (configured locally / failed)
- remote publish: done / skipped

Commands run:
- <list>

Next action:
- continue workflow on this branch (e.g., `$openspec-propose "<change-name>"`, `/plan <change-name>`, `/next-step`)
```

## Guardrails

- Do not run destructive git commands.
- Do not auto-commit.
- Do not bypass invalid branch names or collisions.
- Do not run `pull --ff-only` on dirty tree unless `working_tree=stash`.
- On `working_tree=stash`, stop and report if `stash pop` creates conflicts.

## Reference Baseline

- GitHub Docs (`About branches`, `pull requests`) for branch + PR flow.
- Git docs: `git-fetch`, `git-pull` (`--ff-only`), `git-check-ref-format`, `git-config`.
- Conventional Commits type vocabulary (`feat`, `fix`, `docs`, etc.) for consistent branch prefixes.

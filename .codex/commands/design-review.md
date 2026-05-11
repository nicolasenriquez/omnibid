Execute a comprehensive frontend design review pipeline: evaluate UX + technical quality,
then auto-execute sequenced improvements through the impeccable skill system.

Input: `@ARGUMENTS`

Supported call shapes:
- `/design-review`
- `/design-review <target-path>`
- `/design-review <target-path> scope=evaluate-only|minimal|full`
- `/design-review preflight=off`

Defaults:
- `target=client/`
- `scope=full`
- `preflight=auto`

## Objective

Run a complete **evaluate → improve → polish** pipeline on the frontend using the impeccable skill system:
- Phase 1: Run critique (UX heuristics + anti-patterns) and audit (technical quality) as **parallel** isolated assessments
- Phase 2: Synthesize both assessments into a single prioritized report with P0-P3 severity rankings
- Phase 3: Present report + ask targeted questions tied to specific findings
- Phase 4: Auto-execute fix commands in dependency order per confirmed scope
- Phase 5: Auto-execute enhancement commands in dependency order
- Phase 6: Auto-execute polish as final seal; report before/after score comparison

This command performs code and documentation changes in Phase 4-6.

## Guardrails

- Do not modify files during Phase 1-3 (evaluate, consolidate, ask).
- Do not skip impeccable setup gates (context loader, PRODUCT.md verification, register detection).
- For this codebase (omnibid/ChileCompra procurement app), **default register is `product`** (dashboard/tool/data-heavy application). Override to `brand` only if the target explicitly resolves to a landing/marketing page.
- If PRODUCT.md is missing, empty, or placeholder (`[TODO]` markers, <200 chars): run `$impeccable teach` as a blocking gate before proceeding, then resume.
- Keep changes minimal and scoped to the confirmed target path.
- Respect `scope=evaluate-only` — stops after Phase 3. Do not edit files.
- If any fix/enhance command fails, pause and report rather than silently skipping.
- Never introduce anti-patterns from the impeccable absolute bans list (side-stripe borders, gradient text, glassmorphism as default, hero-metric template, identical card grids).
- Always include a preflight status block before first mutation:

```text
IMPECCABLE_PREFLIGHT: context=pass product=pass command_reference=pass shape=not_required image_gate=skipped:<reason> mutation=open
```

- Read `.codex/skills/impeccable/reference/<command>.md` for each command before executing it.
- Run `npx impeccable --json` for deterministic anti-pattern scanning.

## Process

### Phase 0: Setup

Per `SKILL.md` setup gates, run these steps before any design work.

1. **Context gathering**:
   ```bash
   node .codex/skills/impeccable/scripts/load-context.mjs
   ```
   Consume the full JSON output. If already present in this session's conversation, do not re-run unless you just ran `$impeccable teach` or `$impeccable document`.

2. **PRODUCT.md gate**:
   - If PRODUCT.md is missing, empty, or placeholder: run `$impeccable teach`, refresh context via `load-context.mjs`, then resume with the user's original target.
   - If DESIGN.md is missing: note it once and proceed.

3. **Register detection**:
   - **Default: `product`** for this codebase.
   - This is a data-heavy procurement dashboard/tool application. Design serves the product.
   - Load `reference/product.md`. Only switch to `brand` if target is a landing/marketing page.

4. **Resolve target path**:
   - Default: `client/`
   - Validate the path exists. If it doesn't, stop and ask.
   - Normalize to a path under the repo root.

5. **Resolve scope**:
   - `evaluate-only`: report only, no file changes. Stop after Phase 3.
   - `minimal`: fix P0 issues only.
   - `full`: fix P0-P2 issues. Skip P3 polish-only items.

6. **Output preflight status**:
   ```
   IMPECCABLE_PREFLIGHT: context=pass product=pass command_reference=pass shape=not_required image_gate=skipped:read-only-evaluation mutation=closed
   ```

### Phase 1: Evaluate (parallel, read-only)

Launch two **isolated assessments** simultaneously. Neither may see the other's output.

#### Assessment A: Critique

Follow `reference/critique.md`. This is a UX design review, not a technical audit.

1. **Read target source files**: Walk the resolved target path, read all relevant `.tsx`, `.ts`, `.css`, `.scss`, `.html` files.

2. **LLM Design Review**:
   - AI Slop Detection (review ALL "DON'T" guidelines from the parent SKILL.md)
   - Holistic Design Review: visual hierarchy, information architecture, emotional resonance, discoverability, composition, typography, color, states & edge cases, microcopy
   - Cognitive Load: run the 8-item checklist. Count visible options at decision points. Check progressive disclosure.
   - Emotional Journey: peak-end rule, emotional valleys, design interventions
   - Nielsen's 10 Heuristics: score each 0-4

3. **Deterministic scan**:
   ```bash
   npx impeccable --json client/
   ```
   Flag any false positives.

4. **Persona Red Flags**:
   Auto-select 3 personas relevant to a procurement dashboard:
   - **Alex (Procurement Analyst / Power User)**: Keyboard shortcuts, bulk actions, efficient workflows
   - **Jordan (New Team Member / First-Timer)**: Discoverability, clear labels, onboarding cues
   - **Sarah (Manager / Decision-Maker)**: High-level summary, clear status indicators, export functionality

5. **Return**: Critique report with Design Health Score (/40), Anti-Patterns Verdict, Priority Issues, Persona Red Flags, Positive Findings.

#### Assessment B: Audit

Follow `reference/audit.md`. This is a technical quality check, not a design critique.

Score 5 dimensions (0-4 each):

1. **Accessibility (A11y)**: Contrast ratios (<4.5:1), missing ARIA, keyboard navigation, semantic HTML, alt text, form labeling
2. **Performance**: Layout thrashing, expensive animations, missing lazy loading, bundle size, unnecessary re-renders
3. **Theming**: Hard-coded colors, broken dark mode, inconsistent tokens, theme switching issues
4. **Responsive Design**: Fixed widths, touch targets <44px, horizontal scroll, text scaling, breakpoint gaps
5. **Anti-Patterns**: Check ALL "DON'T" guidelines from SKILL.md. Look for AI slop tells.

**Return**: Audit report with Audit Health Score (/20), rating band, detailed findings by severity, systemic issues, positive findings.

### Phase 2: Consolidate

Synthesize both assessments into a **single Unified Design Review Report**. Do NOT concatenate. Weave findings together, noting where they agree, where the detector caught issues the LLM missed, and where detector findings are false positives.

Output structure:

#### 1. Executive Summary

| Metric | Score | Band |
|---|---|---|
| Design Health (Nielsen /40) | ??/40 | [band] |
| Audit Health (/20) | ??/20 | [band] |
| Overall Verdict | [Excellent / Good / Acceptable / Poor / Critical] |
| Total Issues | P0: N, P1: N, P2: N, P3: N |

Rating bands for critique: 32-40 Excellent, 24-31 Good, 16-23 Acceptable, 8-15 Poor, 0-7 Critical.
Rating bands for audit: 18-20 Excellent, 14-17 Good, 10-13 Acceptable, 6-9 Poor, 0-5 Critical.

#### 2. Anti-Patterns Verdict

**Start here.** Does this look AI-generated?

- **LLM assessment**: Overall aesthetic feel, layout sameness, generic composition, missed personality opportunities.
- **Deterministic scan**: Summarize what the CLI detector found, with counts and file locations. Note false positives.
- **Combined verdict**: Be brutally honest. List specific tells found.

#### 3. Priority Issues

Top 5-8 issues, merged and deduplicated from both assessments. For each:

- `[P0/P1/P2/P3]` severity tag
- **What**: Name the problem clearly
- **Why it matters**: How it hurts users or undermines quality
- **Fix**: Concrete suggestion
- **Suggested command**: Mapped impeccable command (use `$impeccable <command>`)

**Severity definitions**:
- **P0 Blocking**: Prevents task completion, WCAG A violation, or completely broken — fix immediately
- **P1 Major**: Significant difficulty, WCAG AA violation, major aesthetic gap — fix before release
- **P2 Minor**: Annoyance, workaround exists, cosmetic — fix in next pass
- **P3 Polish**: Nice-to-fix, no real user impact — fix if time permits

#### 4. Persona Red Flags

For each selected persona, walk through the primary user action on this interface and list specific red flags found. Be specific — name exact elements and interactions that fail each persona.

#### 5. Positive Findings

Highlight 2-3 things done well. Be specific about why they work.

#### 6. Systemic Issues

Identify recurring problems that indicate systemic gaps rather than one-off mistakes (e.g., "Hard-coded colors appear in 15+ components, should use design tokens").

#### 7. Recommended Actions

Ordered command list. Rules:
- **Dependency order** is fixed — do not reorder:
  1. `$impeccable optimize` — performance first (can touch many files)
  2. `$impeccable harden` — error states, edge cases, i18n (structural)
  3. `$impeccable clarify` — UX copy improvements (low-risk text changes)
  4. `$impeccable adapt` — responsive fixes
  5. `$impeccable typeset` — typography hierarchy
  6. `$impeccable layout` — spacing, rhythm, alignment
  7. `$impeccable colorize` — only if monochrome/color issues found
  8. `$impeccable distill` — only if complexity issues found
  9. `$impeccable bolder` — only if bland/generic issues found
  10. `$impeccable animate` — motion after layout is stable
  11. `$impeccable polish` — always last, final seal
- **Skip** commands that address zero found issues. Do not include them.
- Each entry: `[P?] $impeccable <command> <target-path>` with one-line description carrying specific context from findings.
- `scope=minimal` includes P0 items only. `scope=full` includes P0-P2 items.

### Phase 3: Ask User

Present the report. Then ask 2-4 targeted questions based on the **actual findings** from the report — never generic questions.

Rules for questions:
- Every question must reference specific findings from the report.
- Keep to 2-4 questions maximum.
- Offer concrete options, not open-ended prompts.
- If findings are straightforward (only 1-2 clear issues), skip questions and go directly to Phase 4.

Example template (adapt to actual findings):
1. **Priority**: "I found issues with [categories]. Which area matters most right now?" → offer top 2-3 issue categories as options.
2. **Scope**: "I found N issues. Address everything (full), only P0 (minimal), or top 3 highest-impact?" → offer scope options.
3. **Constraints** (only if many areas touched): "Should any sections stay as-is?" → list sections touched.

**Wait for user answers before proceeding to Phase 4.**

If `scope=evaluate-only`: stop here. Present the report + recommended actions. Do not proceed to Phase 4-6.

### Phase 4: Fix (auto-execute sequentially)

Execute fix commands in dependency order. Each command follows this pattern:

1. Load the command's reference file: `.codex/skills/impeccable/reference/<command>.md`
2. Invoke with target + specific context from the findings report:
   ```
   $impeccable <command> <target-path>
   ```
3. Allow the command to make changes. Pass the specific issues from the report as context.
4. Report result:
   ```
   [PASS] $impeccable <command> <target> → N files changed, M issues addressed
   ```
   or on failure:
   ```
   [FAIL] $impeccable <command> <target> → <reason>
   ```
5. If a command fails: do not abort the entire pipeline. Report the failure, skip to the next command.
6. Scope filtering:
   - `scope=minimal`: execute only commands that address P0 issues.
   - `scope=full`: execute commands addressing P0-P2 issues.
   - Skip commands where all mapped issues are P3.

Commands in this phase: `optimize`, `harden`, `clarify`, `adapt`.

### Phase 5: Elevate (auto-execute sequentially)

Same execution pattern as Phase 4. These run **after** fix commands since they assume a stable baseline.

Commands in this phase: `typeset`, `layout`, `colorize`, `distill`, `bolder`, `animate`, `delight`.

Do NOT run commands that were skipped (zero issues) or filtered out by scope.

### Phase 6: Seal

1. Run `$impeccable polish <target-path>` — final quality pass per `reference/polish.md`.

2. Run a lightweight re-audit:
   - Re-scan `npx impeccable --json <target-path>` for anti-pattern count
   - Re-check the top 3-5 audit dimensions for improvement
   - Do NOT run the full critique + audit again; just diff key metrics

3. Present before/after comparison:

```
## After-Action Report

### Execution Log
| Status | Command | Files | Issues |
|---|---|---|---|
| PASS | $impeccable optimize client/ | 3 | 5 |
| PASS | $impeccable harden client/ | 4 | 3 |
| PASS | $impeccable clarify client/ | 2 | 7 |
| PASS | $impeccable polish client/ | 6 | 12 |

### Score Comparison
| Metric | Before | After |
|---|---|---|
| Anti-Patterns Found | 4 | 1 |
| Audit Score (/20) | 14/20 | 17/20 |
```

## Output Format

### After Phase 3

```
## Unified Design Review Report — `<target-path>`

### 1. Executive Summary
[table with scores, rating bands, issue counts]

### 2. Anti-Patterns Verdict
[LLM assessment + deterministic scan + combined verdict]

### 3. Priority Issues
[top 5-8 issues with P0-P3, what/why/fix/command]

### 4. Persona Red Flags
[per-persona walkthrough with specific elements]

### 5. Positive Findings
[2-3 specific items with why they work]

### 6. Systemic Issues
[recurring patterns indicating systemic gaps]

### 7. Recommended Actions
[ordered, scoped command list with skip annotations]

### 8. Ask User
[2-4 targeted questions derived from actual findings]
```

### After Phase 6

```
## After-Action Report

### Execution Log
[per-command status, file count, issue count]

### Failed Commands
[skipped on success]

### Score Comparison
[before/after table for key metrics]

### Remaining Issues
[unresolved P2-P3 items if any]

### Recommended Next Command
/commit-local "design review: elevate <target> UX quality"
```

## Definition of Done

This command is complete when:
- Setup gates passed (context, product, register)
- Critique and audit assessments ran as isolated parallel evaluations
- Unified report presented with actionable issue mappings
- User confirmed scope and priorities (unless `evaluate-only`)
- All fix and enhancement commands executed in dependency order (or Phase 3 stop point reached)
- Failed commands explicitly reported with reasons
- Polish ran as final quality seal
- Before/after score comparison included
- One concrete next command recommended
- No anti-patterns from the absolute bans list were introduced
- Files are clean (no `[TODO]` markers left from Phase 0-3 read-only work)

## Error Handling

- **Missing PRODUCT.md**: Block and run `$impeccable teach` first. Resume after.
- **Missing target path**: Stop and ask user for a valid path.
- **CLI detector failure**: Continue with LLM-only critique. Note the gap.
- **Command execution failure**: Log `[FAIL]`, continue to next command. Do not abort the full pipeline.
- **`$impeccable teach` requested during setup**: Complete it, refresh context, then resume the full pipeline.
- **Ambiguous register**: Default to `product`. If the target is clearly a landing page, switch to `brand`.

## Never

- Edit files before the preflight status reports `mutation=open`
- Combine critique and audit assessments in one head (they must be isolated)
- Ask generic questions not tied to specific findings
- Reorder the command dependency chain
- Run skipped commands (zero mapped issues)
- Execute Phase 4-6 when `scope=evaluate-only`
- Introduce side-stripe borders, gradient text, glassmorphism, hero metrics, or identical card grids
- Use gray text on colored backgrounds
- Use pure black (`#000`) or pure white (`#fff`)
- Use bounce or elastic easing
- Polish before the feature is functionally complete
- Forget to include before/after comparison

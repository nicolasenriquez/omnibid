# Long-Running Agent Harness

## Purpose

Use this runbook when an agent is expected to work across multiple turns, touch more than one subsystem, or make decisions that depend on business meaning, table grain, or source provenance.

The goal is to keep the loop:

1. grounded in repo truth
2. explicit about what data means
3. bounded by a durable validation path
4. safe to resume after context loss

## Canonical Inputs

Start from these repo sources before editing code or docs:

- `AGENTS.md`
- `README.md`
- `docs/README.md`
- `docs/business/agent_context_pack.md`
- `docs/business/domain_glossary.md`
- `docs/architecture/system_architecture.md`
- `docs/architecture/data_architecture.md`
- `docs/architecture/data_model.md`
- `docs/architecture/external_api_ingestion.md`
- `docs/standards/customer-analytics-standards.md`
- `docs/standards/logging-standard.md`
- `docs/runbooks/docker-local.md`
- `docs/references/sdd-official-sources-registry.md`

If a change touches procurement meaning, also read the relevant domain note or SDD record before mutating code.

## Harness Loop

### 1. Restate the job

Write down:

- who the work serves
- what decision it enables
- what is in scope
- what is out of scope
- what success looks like

If that cannot be stated in one short paragraph, the task is not ready for implementation.

### 2. Lock the contracts

Confirm:

- the source contract
- the business grain
- the primary keys or conflict keys
- the optional links that must remain optional
- the runtime path for validation

Never guess these from a downstream view model or UI label.

### 3. Pick one execution surface

Use the smallest surface that can prove the change:

- backend/data work: Docker-first `just` recipe
- browser-facing work: static inspection first, then browser verification
- docs-only work: source docs plus the affected markdown files

Prefer one minimal proof before broad changes.

### 4. Produce a working set artifact

For each long-running change, keep a short working set note in the task or change artifact with:

- problem statement
- relevant docs and source registry entries
- table or DTO grain
- assumptions
- validation command
- known open questions

This note is the handoff object for the next agent turn.

### 5. Validate before expanding scope

Validate the narrowest safe slice first:

- unit tests for contract or transformation logic
- database-backed checks for writes or joins
- Docker smoke for runtime paths
- browser verification for UI work

Do not expand to adjacent subsystems until the first proof passes.

## Shared Evaluation Rubric

Score the change against these five questions:

| Category | Pass condition |
| --- | --- |
| Business context | The change names the user, operator, or decision-maker and states why the data matters. |
| Data grain | The change respects the correct entity grain and does not collapse child facts into parent rows. |
| Provenance | The change cites the source docs, official docs, or SDD note that justify the contract. |
| Runtime validation | The change has a reproducible command or browser path that proves behavior. |
| UI semantics | User-facing copy stays separated from raw backend field names and internal implementation details. |

Minimum bar:

- all five categories are satisfied
- any unresolved ambiguity is written down
- any skipped validation has a reason

## Stop Conditions

Stop and ask rather than guessing when:

- the source contract is unclear
- the table grain is ambiguous
- a link that should be optional is being treated as mandatory
- the task would require inventing business meaning
- the validation path is missing or unstable

## Evidence Template

Use [`agent-working-set-template.md`](agent-working-set-template.md) for the canonical note shape.

Keep the note short and update it as the work evolves. The template should capture:

- the problem statement
- the docs and source registry entries that justify the contract
- the entity or DTO grain
- the assumptions that are still in play
- the validation command or browser path
- the current trace or run ID
- the open questions that remain

## Non-Goals

- Do not add agent orchestration into product runtime.
- Do not replace the existing OpenSpec or command workflow.
- Do not infer business truth from UI state alone.
- Do not persist agent narrative as canonical data.

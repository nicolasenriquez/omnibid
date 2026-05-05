# SDD Reference Note

## Metadata

- Change/Proposal: fasttext-standard-documentation
- Date: 2026-05-05
- Author: Codex
- Area (backend/db/pipeline/api/tooling): docs / NLP / classification

## Question

- Which fastText supervised-classification and model-size contracts should be standardized for reproducible NLP work in this repository?

## Official Sources Consulted

1. https://fasttext.cc/docs/en/supervised-tutorial.html
   - Section/topic: supervised text classification, training data, evaluation, prediction, and multi-label behavior
   - Relevant contract: training requires labeled UTF-8 data with `__label__` prefixes; validation should use held-out data; predictions can be thresholded for multi-label work
2. https://fasttext.cc/docs/en/api.html
   - Section/topic: CLI and Python API surface
   - Relevant contract: `train_supervised`, `test`, `predict`, `predict-prob`, `load_model`, and related entry points are the documented API surface
3. https://fasttext.cc/docs/en/supervised-models.html
   - Section/topic: supervised model zoo and quantization
   - Relevant contract: quantized models are a supported deployment form, but the quality tradeoff should be treated explicitly

## Repository Notes Consulted

1. `docs/standards/nlp-standards.md`
   - Section/topic: broader NLP boundary
   - Relevant contract: fastText is already the repository's offline language-identification layer and must remain aligned with the Silver-first NLP boundary

## Decision

- What was implemented: created `docs/standards/fasttext-standard.md`, added fastText sources to the official registry, and recorded the source-backed rationale in a dedicated SDD note.
- Why this matches official source: the fastText tutorial explicitly defines the supervised workflow around labeled UTF-8 data, held-out evaluation, prediction, multi-label thresholding, and model size reduction through quantization.

## Code Impact

- Files touched:
  - `docs/standards/fasttext-standard.md`
  - `docs/references/sdd-fasttext-standard-2026-05-05.md`
  - `docs/references/sdd-official-sources-registry.md`
  - `docs/standards/engineering_standards.md`
  - `docs/standards/nlp-standards.md`
- Behavioral impact:
  - no runtime behavior changed
  - the repository now has a dedicated supervised fastText contract layered under the broader NLP standard

## Validation

- Tests/checks executed:
  - reviewed the current NLP standard and the SDD template
  - checked the official fastText supervised tutorial, API page, and supervised-models page
- Result:
  - the documentation was generated successfully with source-backed rules and repo-context alignment

## Notes / Risks

- Open questions:
  - whether future work will need a separate fastText language-identification standard
  - whether the repository should pin a specific fastText release or treat it as a pure doc-level contract
- Follow-up actions:
  - keep any implementation work aligned with the dedicated fastText standard and the broader NLP boundary
  - add examples only when a concrete classifier pipeline lands in code

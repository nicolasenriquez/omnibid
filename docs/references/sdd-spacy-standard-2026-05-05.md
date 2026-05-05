# SDD Reference Note

## Metadata

- Change/Proposal: spacy-standard-documentation
- Date: 2026-05-05
- Author: Codex
- Area (backend/db/pipeline/api/tooling): docs / NLP / pipeline

## Question

- Which spaCy pipeline, rule-based, and Spanish-model contracts should be standardized for reproducible NLP work in this repository?

## Official Sources Consulted

1. https://spacy.io/api/
   - Section/topic: library architecture
   - Relevant contract: spaCy centers on `Language`, `Doc`, `Token`, `Span`, and pipeline components
2. https://spacy.io/api/language/
   - Section/topic: pipeline orchestration and component registration
   - Relevant contract: load one pipeline per process, process documents in order, and add registered components explicitly
3. https://spacy.io/usage/linguistic-features
   - Section/topic: tokenization, POS, morphology, lemmatization, and entity annotations
   - Relevant contract: linguistic annotations are explicit token attributes and rule-based lemmatization depends on prior annotations
4. https://spacy.io/models/es/
   - Section/topic: Spanish trained pipelines
   - Relevant contract: the Spanish model family includes `es_core_news_sm`, `es_core_news_md`, `es_core_news_lg`, and `es_dep_news_trf`
5. https://spacy.io/api/entityruler
   - Section/topic: rule-based entity recognition
   - Relevant contract: `EntityRuler` can add phrase- or token-based entities and can combine with statistical NER
6. https://spacy.io/api/spanruler
   - Section/topic: span and entity span augmentation
   - Relevant contract: `SpanRuler` can write spans to `Doc.spans` and/or `Doc.ents`
7. https://spacy.io/usage/rule-based-matching/
   - Section/topic: matcher and phrase matcher guidance
   - Relevant contract: rules are appropriate for finite or structured patterns and can bootstrap statistical models
8. https://spacy.io/api/attributeruler
   - Section/topic: token attribute exceptions and mappings
   - Relevant contract: `AttributeRuler` is the explicit place for deterministic token attribute mappings and exceptions
9. https://spacy.io/api/attributes/
   - Section/topic: token attribute naming and access
   - Relevant contract: use documented token attributes and the `_` suffix for string forms
10. https://spacy.io/api/span
   - Section/topic: span behavior
   - Relevant contract: spans are explicit document slices with labels and IDs

## Repository Notes Consulted

1. `docs/standards/nlp-standards.md`
   - Section/topic: broader NLP boundary
   - Relevant contract: spaCy is already the canonical Spanish linguistic pipeline in the repo
2. `docs/references/sdd-nlp-standards-2026-05-05.md`
   - Section/topic: repo NLP source note
   - Relevant contract: Silver NLP outputs remain metadata-only and deterministic

## Decision

- What was implemented: created `docs/standards/spacy-standard.md`, added spaCy sources to the official registry, and recorded the source-backed rationale in a dedicated SDD note.
- Why this matches official source: spaCy’s docs explicitly define the pipeline, token/Doc/span objects, rule-based matching components, and Spanish model families, which gives a clean contract for reproducible NLP work.

## Code Impact

- Files touched:
  - `docs/standards/spacy-standard.md`
  - `docs/references/sdd-spacy-standard-2026-05-05.md`
  - `docs/references/sdd-official-sources-registry.md`
  - `docs/standards/engineering_standards.md`
  - `docs/standards/nlp-standards.md`
- Behavioral impact:
  - no runtime behavior changed
  - the repository now has a dedicated spaCy contract layered under the broader NLP standard

## Validation

- Tests/checks executed:
  - reviewed the current NLP standard and the SDD template
  - checked the official spaCy docs for pipeline, rule-based matching, attributes, and Spanish model behavior
- Result:
  - the documentation was generated successfully with source-backed rules and repo-context alignment

## Notes / Risks

- Open questions:
  - whether the repository will later standardize a specific spaCy model version pin beyond the current family choice
  - whether future work needs a separate standard for spaCy training and config management
- Follow-up actions:
  - keep any implementation work aligned with the dedicated spaCy standard and the broader NLP boundary
  - add examples only when a concrete pipeline lands in code

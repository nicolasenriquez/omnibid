# spaCy Standard: deterministic linguistic pipelines, rule-based augmentation, and reproducible Spanish NLP

## Overview

spaCy is the canonical in-process NLP library for this repository's Spanish text processing work.
Use it for tokenization, sentence segmentation, part-of-speech tagging, lemmatization, dependency parsing, named entity recognition, rule-based matching, and structured span extraction.

spaCy is an analysis layer, not a persistence layer. Keep the original source text, derived annotations, and any downstream artifacts separate and versioned.

## Scope

This standard applies to:

- Spanish text processing pipelines
- tokenization and sentence segmentation
- part-of-speech, morphology, lemma, dependency, and entity annotations
- rule-based matching and span/entity augmentation
- custom spaCy pipeline components and language data
- pipeline serialization, ruler pattern files, and reproducible batch processing

This standard does not define:

- database schema or Silver persistence contracts
- unrelated ML model serving
- ad hoc notebook experiments without reusable inputs
- downstream embeddings or ranking layers outside spaCy

## Source Priority

Use sources in this order:

1. Official spaCy documentation
2. Repository NLP standards and architecture docs
3. Repository environment and runtime contracts
4. Secondary sources only when official docs do not cover the behavior

## Repository Context

This standard narrows the broader NLP boundary already defined in `docs/standards/nlp-standards.md`.
The repository standard treats spaCy as the canonical Spanish linguistic pipeline and uses rule-based augmentation for deterministic procurement text handling.

If you maintain a separate course or notebook note collection, keep it aligned with this doc by versioning the model name, pipeline order, and pattern files explicitly.

## Canonical Stack

- `spacy.Language` for pipeline orchestration
- `Doc`, `Token`, `Span`, and `SpanGroup` as the annotation objects
- `EntityRuler` and `SpanRuler` for deterministic span/entity augmentation
- `AttributeRuler` for token-attribute exceptions and mappings
- `es_core_news_md` as the canonical Spanish model for this repository
- `spacy-lookups-data` when a custom or lookup-based lemmatizer needs external tables

Use trained pipelines for linguistic predictions and rule-based components for deterministic domain-specific augmentation.

## Core Usage Rules

### 1. Load one pipeline per process

- Create the `nlp` object once and pass it through the application.
- Use `spacy.load(...)` for a trained pipeline and `spacy.blank(...)` only when you intentionally need a blank language object.
- Do not reload the pipeline repeatedly inside hot loops.

### 2. Use registered components

- Add custom components with `@Language.component` or `@Language.factory`.
- Add them through `nlp.add_pipe(...)` by registered name.
- Do not rely on anonymous callables as the long-term contract.

### 3. Batch with `nlp.pipe`

- Use `nlp.pipe` for batches of texts.
- Prefer streaming batches over one-document-at-a-time loops when throughput matters.
- Keep batch size explicit when performance or memory behavior matters.

### 4. Keep tokenization explicit

- Treat tokenization as the first contract in the pipeline.
- Avoid custom tokenizer subclassing unless the domain has a stable, documented tokenization rule that the default tokenizer cannot express.
- Use tokenizer exceptions and language data before writing a fully custom tokenizer.

### 5. Respect annotation order

- If lemmatization depends on POS or morphological information, ensure the POS or morphologizer step runs first.
- If rule-based mappings are needed, use `AttributeRuler` rather than scattering ad hoc fixes across components.
- Keep pipeline order documented when custom components depend on earlier annotations.

### 6. Use rule-based augmentation where the task is finite or structured

- Use `EntityRuler` for exact phrases or token-rule entity augmentation.
- Use `SpanRuler` when spans need to be stored in `Doc.spans`, `Doc.ents`, or both.
- Use rule-based augmentation to bootstrap or stabilize extraction when the pattern set is finite and well understood.
- Prefer statistical models when the task needs broad generalization and enough labeled data exists.

### 7. Version patterns and component config

- Keep ruler patterns in versioned JSONL files or other explicit artifacts.
- Keep component configuration in the pipeline config or serialized pipeline assets.
- Do not hide rule changes inside notebooks without a persisted pattern file.

### 8. Keep model choice intentional

- Use the named Spanish model family explicitly.
- The repository default is `es_core_news_md` because it balances linguistic coverage and vectors well enough for the current workflow.
- Do not assume `sm` packages include word vectors.

### 9. Treat similarity and vectors carefully

- Only rely on vector similarity when the loaded pipeline actually provides vectors.
- Do not use similarity scores as a substitute for deterministic extraction contracts.
- Keep vector-enabled and vector-free behavior explicit in tests.

### 10. Keep serialization and reload behavior explicit

- Use `to_disk` / `from_disk` for reproducible pipeline or ruler persistence.
- Make sure saved patterns, configs, and model names are versioned together.
- Do not treat notebook state as a durable spaCy artifact.

## Approved spaCy Patterns

Use these patterns as the default building blocks:

| Analysis intent | Preferred spaCy area |
| --- | --- |
| Load and run a language pipeline | `Language` |
| Process many documents efficiently | `Language.pipe` |
| Tokenize raw text | tokenizer and `Doc` |
| Inspect POS, lemma, morph, dependency, and entities | `Token` / `Doc` annotations |
| Add deterministic entity labels | `EntityRuler` |
| Add deterministic span annotations | `SpanRuler` |
| Normalize or map token attributes | `AttributeRuler` |
| Combine rules with statistical annotations | rule-based matching plus trained pipeline |
| Export analysis visuals | explicit visualization output |

## Text Processing Contract

Process text in a deterministic order:

1. keep the source text intact
2. normalize input encoding before it enters the pipeline
3. apply the chosen spaCy model consistently
4. keep derived lowercase or stripped forms as separate outputs if needed
5. preserve the original text for traceability

Do not overwrite source text with derived analysis text.

## Sentence and Span Rules

- Use sentence boundaries intentionally.
- If deterministic sentence splitting is enough, prefer a rule-based sentence component over a heavier parser dependency.
- Keep overlapping span behavior explicit when using `SpanRuler`.
- Remember that `Doc.ents` does not allow arbitrary overlapping entities.

## Pitfalls and Required Guards

- Rule-based lemmatization depends on prior POS or morphology.
- `EntityRuler` patterns should be validated and versioned when they affect business extraction.
- `SpanRuler` and `EntityRuler` are not interchangeable; choose based on the target storage surface.
- `sm` model packages do not ship word vectors.
- `nlp.pipe` is the preferred batch interface; one-by-one processing is slower and noisier to test.
- Custom tokenization should be the exception, not the default.
- Global notebook state can make spaCy behavior appear stable when it is actually implicit.

## Testing Rules

- Assert tokenization boundaries with explicit expected token sequences.
- Assert sentence boundaries when sentence splitting is part of the contract.
- Assert POS, lemma, and entity outputs on fixture text.
- Test rule-based patterns as versioned fixtures, not as inline notebook state.
- Add regression tests when pipeline order matters.
- Use deterministic seeds or fixed inputs for any workflow that depends on stochastic sampling outside spaCy.

## Validation Commands

When spaCy behavior changes in code, validate with the repository gates that match the impacted surface:

```bash
rtk just docker-start
rtk just docker-smoke
rtk just ci-fast
```

If the change is limited to documentation, validate the markdown and links only.

## Official Sources Consulted

| Source | Topic | Decision |
| --- | --- | --- |
| https://spacy.io/api/ | Library architecture | Treat `Language`, `Doc`, `Token`, `Span`, and pipeline components as the core API surface |
| https://spacy.io/api/language/ | Pipeline orchestration and component registration | Load one pipeline per process, add components by registered name, and process docs in order |
| https://spacy.io/usage/linguistic-features | Tokenization, POS, lemmatization, morphology, entities | Keep linguistic annotations explicit and respect annotation ordering |
| https://spacy.io/models/es/ | Spanish model families | Use the named Spanish pipeline family explicitly and keep the repository default model choice documented |
| https://spacy.io/api/entityruler | Rule-based entity recognition | Use deterministic entity augmentation when the pattern set is finite and versionable |
| https://spacy.io/api/spanruler | Span and entity span augmentation | Use `SpanRuler` when spans need to be stored in `Doc.spans` and/or `Doc.ents` |
| https://spacy.io/usage/rule-based-matching/ | Matcher and PhraseMatcher guidance | Prefer rule-based matching for finite or bootstrapping tasks and keep pattern logic explicit |
| https://spacy.io/api/attributeruler | Token attribute exceptions and mappings | Use `AttributeRuler` for deterministic token-attribute fixes and mappings |
| https://spacy.io/api/attributes/ | Token attribute names and access | Use the documented token attribute contract and the `_` suffix for string forms |
| https://spacy.io/api/span | Span object behavior | Treat spans as explicit slices of a document with their own labels and identifiers |

## Repository Notes Consulted

| Source | Topic | Decision |
| --- | --- | --- |
| `docs/standards/nlp-standards.md` | Repository NLP boundary | Keep spaCy aligned with the broader Silver-first NLP contract |
| `docs/references/sdd-nlp-standards-2026-05-05.md` | Repo NLP SDD note | Reuse the existing source-backed NLP boundary and avoid drifting from the Silver contract |

## Notes

This standard is intentionally conservative.
It gives spaCy a dedicated contract so future changes can evolve the NLP pipeline without re-litigating the same component-order and rule-based matching decisions.

**Last Updated:** 2026-05-05

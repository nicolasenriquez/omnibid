# fastText Standard: supervised text classification, label discipline, and reproducible lightweight models

## Overview

fastText is the canonical lightweight text-classification library for this repository when the task is supervised label prediction.
Use it for fast baseline classifiers, multi-label text categorization, and compact models that are easy to train, evaluate, and deploy.

fastText is not a replacement for careful dataset design.
Its quality depends heavily on labeled inputs, preprocessing discipline, and explicit validation.

## Scope

This standard applies to:

- supervised text classification
- multi-label text classification
- training data preparation and label formatting
- validation and held-out evaluation
- model export, loading, and quantization for small-footprint use cases
- fastText-based batch or CLI workflows

This standard does not define:

- word-vector research workflows
- general embedding model serving
- database schema or persistence contracts
- notebook-only experiments without reproducible inputs

## Source Priority

Use sources in this order:

1. Official fastText documentation
2. Repository NLP standards and architecture docs
3. Repository environment and runtime contracts
4. Secondary sources only when official docs do not cover the behavior

## Repository Context

This standard narrows the broader NLP boundary already defined in `docs/standards/nlp-standards.md`.
The repository already uses fastText as the offline language-identification layer, and this document defines the supervised-classification workflow with the same source-backed discipline.

If you later add course notes or notebook examples, keep them aligned to this standard by versioning the label prefix, preprocessing rules, and evaluation metrics explicitly.

## Canonical Stack

- `fasttext.train_supervised` for supervised training
- `fasttext.FastText.load_model` for loading trained models
- `model.test(...)` or the `test` subcommand for validation
- `model.predict(...)` and `model.predict(..., threshold=...)` for inference
- `predict-prob` for multi-label workflows where label thresholds matter
- `quantize` for reducing model size after baseline validation

Use the CLI or Python API intentionally, not interchangeably by accident.
Choose one primary path for a given workflow and keep the commands versioned.

## Core Usage Rules

### 1. Require labeled training data for supervised work

- Each training line must contain at least one label.
- Labels must use the `__label__` prefix.
- Keep labels before the document text on each line.
- Do not mix unlabeled text into supervised training files.

### 2. Preprocess the corpus explicitly

- Encode the training corpus as UTF-8 before training.
- Normalize punctuation, whitespace, and casing explicitly when the task benefits from it.
- Keep preprocessing deterministic and documented.
- Do not rely on implicit tokenization side effects to clean the corpus for you.

### 3. Split train, validation, and test sets deliberately

- Use a held-out validation set before claiming model quality.
- Keep the split reproducible.
- Do not tune on the validation set and then report validation metrics as if they were test metrics.

### 4. Measure the right metric for the task

- Use `P@k` and `R@k` for classification quality checks.
- For multi-label workflows, tune `k` and the probability threshold together.
- Do not judge a classifier from one or two example predictions.

### 5. Tune the simplest levers first

- Start with preprocessing quality.
- Then tune `epoch`, learning rate, and n-gram settings when the official workflow requires better separation.
- Keep the model and argument set versioned so results are reproducible.

### 6. Use thresholds intentionally for multi-label prediction

- Use `predict-prob` when you need probabilities.
- Tune the threshold on validation data, not on the test set.
- Keep the selected threshold documented with the model artifact.

### 7. Save, load, and ship models explicitly

- Save trained models as versioned artifacts.
- Load them back with the documented API rather than rebuilding them implicitly.
- Keep model paths, corpus versions, and training arguments together in the artifact record.

### 8. Quantize only after baseline quality is known

- Use quantization to reduce memory usage when footprint matters.
- Quantize only after you have a measured baseline.
- Re-check quality after quantization because size reduction can affect accuracy.

### 9. Keep task boundaries clear

- Use supervised fastText for classification tasks.
- Use a separate standard for language identification or other NLP layers when needed.
- Do not mix classifier labels, raw text, and artifact metadata without an explicit schema or file contract.

## Approved fastText Patterns

Use these patterns as the default building blocks:

| Analysis intent | Preferred fastText area |
| --- | --- |
| Train a baseline classifier | `train_supervised` |
| Evaluate classifier quality | `test` / `model.test(...)` |
| Predict top labels | `predict` / `model.predict(...)` |
| Predict labels with probabilities | `predict-prob` / `threshold` |
| Reduce model memory footprint | `quantize` |
| Persist a trained model | `save_model` / `load_model` |

## Training Data Contract

The training file should follow a simple, explicit structure:

1. one example per line
2. one or more labels at the start of the line
3. labels prefixed with `__label__`
4. document text after the labels
5. UTF-8 encoded content

Do not use the supervised format for unlabeled corpora.

## Validation Contract

Use validation to check model quality before you optimize for size or speed.

- keep a held-out validation file separate from training
- report `P@k` and `R@k`
- capture the command arguments used to train and test
- compare model versions against the same evaluation split when possible

For multi-label tasks:

- use `k = -1` and an explicit threshold when you need all labels above a confidence cutoff
- keep the threshold selection documented with the model version

## Pitfalls and Required Guards

- Unlabeled lines do not belong in supervised training data.
- `__label__` is part of the contract, not a stylistic convention.
- Accuracy on a single example does not prove generalization.
- Validation and test sets should not be conflated.
- Quantization changes the deployed model profile and should be revalidated.
- Over-normalizing text can remove signal; normalize only as much as the task needs.
- Training files must be UTF-8 encoded.

## Testing Rules

- Assert that training examples are formatted with the correct label prefix.
- Assert that preprocessing is deterministic.
- Keep corpus splits reproducible and fixture-backed.
- Compare model metrics on a fixed validation split.
- Re-run quality checks after quantization or label-taxonomy changes.

## Validation Commands

When fastText behavior changes in code, validate with the repository gates that match the impacted surface:

```bash
rtk just compose-up
rtk just docker-smoke
rtk just ci-fast
```

If the change is documentation-only, validate the markdown and links only.

## Official Sources Consulted

| Source | Topic | Decision |
| --- | --- | --- |
| https://fasttext.cc/docs/en/supervised-tutorial.html | Supervised text classification workflow | Use labeled data, explicit preprocessing, validation, prediction, and multi-label thresholding as the core workflow |
| https://fasttext.cc/docs/en/api.html | Python and CLI API surface | Use the documented training, loading, testing, and prediction entry points intentionally |
| https://fasttext.cc/docs/en/supervised-models.html | Quantized supervised models | Treat quantization as a size-reduction step that must be revalidated |

## Repository Notes Consulted

| Source | Topic | Decision |
| --- | --- | --- |
| `docs/standards/nlp-standards.md` | Broader NLP boundary | Keep fastText aligned with the repository's Silver-first NLP contract |
| `docs/references/sdd-nlp-standards-2026-05-05.md` | Repo NLP source note | Reuse the existing source-backed NLP boundary and keep supervised fastText separate from the classifier contract |

## Notes

This standard is intentionally conservative.
It defines a reproducible supervised-classification baseline so future fastText work can be validated against explicit label and metric contracts instead of notebook habits.

**Last Updated:** 2026-05-05

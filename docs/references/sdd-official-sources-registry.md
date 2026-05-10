# Official Sources Registry (SDD)

This registry defines the preferred official sources for this repository stack.

## Runtime and Language

- Python: https://docs.python.org/3/
- Python `argparse`: https://docs.python.org/3/library/argparse.html
- Python `csv`: https://docs.python.org/3/library/csv.html
- Python `datetime`: https://docs.python.org/3/library/datetime.html
- Python `hashlib`: https://docs.python.org/3/library/hashlib.html
- Python `json`: https://docs.python.org/3/library/json.html
- Python `pathlib`: https://docs.python.org/3/library/pathlib.html
- Python `unicodedata`: https://docs.python.org/3/library/unicodedata.html
- uv: https://docs.astral.sh/uv/
- Just: https://just.systems/man/en/
- Docker Engine/Compose: https://docs.docker.com/

## API and Validation

- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://docs.pydantic.dev/

## Persistence and Migrations

- SQLAlchemy 2.x: https://docs.sqlalchemy.org/en/20/
- Alembic: https://alembic.sqlalchemy.org/en/latest/
- PostgreSQL 16: https://www.postgresql.org/docs/16/

## Supabase CLI and Deployment

- Supabase CLI getting started: https://supabase.com/docs/guides/local-development/cli/getting-started
- Supabase local development with schema migrations: https://supabase.com/docs/guides/cli/local-development
- Supabase config and secrets: https://supabase.com/docs/guides/local-development/managing-config
- Supabase database migrations: https://supabase.com/docs/guides/deployment/database-migrations
- Supabase Postgres connection strings and pooler modes: https://supabase.com/docs/guides/database/connecting-to-postgres/serverless-drivers

## NLP, Text Processing, and Settings

- spaCy API architecture: https://spacy.io/api/
- spaCy Language API: https://spacy.io/api/language/
- spaCy linguistic features: https://spacy.io/usage/linguistic-features
- spaCy Spanish models: https://spacy.io/models/es/
- spaCy EntityRuler: https://spacy.io/api/entityruler
- spaCy SpanRuler: https://spacy.io/api/spanruler
- spaCy AttributeRuler: https://spacy.io/api/attributeruler
- spaCy attributes: https://spacy.io/api/attributes/
- spaCy rule-based matching: https://spacy.io/usage/rule-based-matching/
- fastText language identification: https://fasttext.cc/docs/en/language-identification
- scikit-learn CountVectorizer: https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.CountVectorizer.html
- scikit-learn TfidfVectorizer: https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html
- NLTK SnowballStemmer: https://www.nltk.org/api/nltk.stem.SnowballStemmer.html
- fastText supervised tutorial: https://fasttext.cc/docs/en/supervised-tutorial.html
- fastText API: https://fasttext.cc/docs/en/api.html
- fastText supervised models: https://fasttext.cc/docs/en/supervised-models.html
- Hugging Face Tokenizers: https://huggingface.co/docs/tokenizers/index
- Hugging Face tokenization pipeline: https://huggingface.co/docs/tokenizers/pipeline
- Hugging Face Transformers pipelines: https://huggingface.co/docs/transformers/main_classes/pipelines
- Sentence Transformers usage: https://sbert.net/docs/sentence_transformer/usage/usage.html
- Sentence Transformers pretrained models: https://sbert.net/docs/sentence_transformer/pretrained_models.html
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

## Graphs and Network Analysis

- NetworkX reference index: https://networkx.org/documentation/stable/reference/index.html
- NetworkX introduction: https://networkx.org/documentation/stable/reference/introduction.html
- NetworkX graph types: https://networkx.org/documentation/stable/reference/classes/index.html
- NetworkX randomness: https://networkx.org/documentation/stable/reference/randomness.html
- NetworkX graph drawing: https://networkx.org/documentation/stable/reference/drawing.html
- NetworkX graph reading and writing: https://networkx.org/documentation/stable/reference/readwrite/
- NetworkX GraphML: https://networkx.org/documentation/stable/reference/readwrite/graphml.html
- NetworkX GEXF: https://networkx.org/documentation/stable/reference/readwrite/gexf.html
- NetworkX edge lists: https://networkx.org/documentation/stable/reference/readwrite/edgelist.html
- NetworkX config: https://networkx.org/documentation/stable/reference/configs.html

## Testing and Quality

- pytest: https://docs.pytest.org/en/stable/
- mypy: https://mypy.readthedocs.io/en/stable/
- Ruff: https://docs.astral.sh/ruff/
- Pyright: https://microsoft.github.io/pyright/
- Bandit: https://bandit.readthedocs.io/en/latest/

## CI/CD and Supply Chain

- GitHub Actions workflow syntax: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- GitHub Actions trigger behavior: https://docs.github.com/en/actions/using-workflows/triggering-a-workflow
- GitHub Actions token permissions: https://docs.github.com/en/actions/security-guides/automatic-token-authentication
- GitHub Actions hardening: https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions
- GitHub Actions service containers: https://docs.github.com/en/actions/guides/about-service-containers
- Dependabot supported ecosystems: https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-and-repositories
- Dependabot options reference: https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference
- Docker CI/build docs: https://docs.docker.com/build/ci/
- pre-commit: https://pre-commit.com/
- Gitleaks action: https://github.com/gitleaks/gitleaks-action

## OpenSpec Workflow

- OpenSpec (project local conventions): `openspec/` artifacts in this repository

## Usage Rule

When implementing behavior tied to one of these tools/frameworks:

1. start from this registry
2. consult the matching official source
3. document the resulting decision in an SDD note/template record

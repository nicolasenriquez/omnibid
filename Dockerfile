FROM python:3.13-slim@sha256:a0779d7c12fc20be6ec6b4ddc901a4fd7657b8a6bc9def9d3fde89ed5efe0a3d AS app

COPY --from=ghcr.io/astral-sh/uv:0.8.15@sha256:a5727064a0de127bdb7c9d3c1383f3a9ac307d9f2d8a391edc7896c54289ced0 /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app --home /home/app app \
    && mkdir -p /app/data /tmp/uv-cache \
    && chown app:app /app /tmp/uv-cache

USER app

COPY --chown=app:app pyproject.toml uv.lock README.md alembic.ini ./
COPY --chown=app:app alembic ./alembic

RUN uv sync --frozen --no-install-project --no-dev

COPY --chown=app:app backend ./backend
COPY --chown=app:app scripts ./scripts

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

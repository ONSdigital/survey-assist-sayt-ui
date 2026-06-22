# syntax=docker/dockerfile:1.7
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_HOME=/opt/poetry \
    POETRY_VERSION=2.1.3 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="${POETRY_HOME}/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

COPY pyproject.toml ./
COPY src ./src
COPY scripts ./scripts
COPY .design-system-version ./

RUN poetry install --without dev --no-root
RUN ./scripts/fetch_ons_templates.sh
RUN .venv/bin/pip install --no-cache-dir gunicorn==23.0.0

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}" \
    PORT=8000

WORKDIR /app

RUN groupadd --system app \
    && useradd --system --gid app --home /home/app --create-home app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

RUN chown -R app:app /app
USER app

EXPOSE 8000
CMD ["/bin/sh", "-c", "exec python -m gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 8 --timeout 60 --chdir /app/src 'survey_assist_sayt_ui.app:create_app()'"]

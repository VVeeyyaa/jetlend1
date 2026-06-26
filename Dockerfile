FROM ghcr.io/jitesoft/python:3.12.3

RUN apk add --no-cache \
    tini \
    postgresql-dev \
    gcc \
    musl-dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app:$PYTHONPATH"

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock* /app/

RUN poetry config virtualenvs.create false \
    && poetry lock --no-interaction --no-ansi \
    && poetry install --no-root --no-interaction --no-ansi

COPY app/ /app/

ENTRYPOINT ["tini", "--"]

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
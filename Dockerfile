FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 10000

CMD ["sh", "-c", "\
    exec uv run gunicorn src.main:app \
        --workers ${WEB_CONCURRENCY:-2} \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:${PORT:-10000} \
        --timeout 120 \
        --access-logfile - \
"]

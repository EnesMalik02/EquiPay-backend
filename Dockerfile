FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .

EXPOSE 8000
USER 1001

CMD ["gunicorn", "src.main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--access-logfile", "-"]

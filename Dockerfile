FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.11 /uv /usr/local/bin/uv
WORKDIR /app
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy ANONYMIZED_TELEMETRY=False
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app
COPY reports/saved-example.json reports/evaluation.json ./reports/
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app/app/data
USER appuser
ENV PATH="/app/.venv/bin:$PATH" PORT=8080
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]

FROM python:3.12-slim
# та же версия uv, что создала uv.lock
RUN pip install --no-cache-dir uv==0.11.32
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
EXPOSE 8000
# ingest идемпотентен и дешёв (кэш LLM в БД), поэтому выполняется при каждом старте
CMD ["sh", "-c", "uv run --no-dev python -m app.ingest && uv run --no-dev uvicorn app.api.main:app --host 0.0.0.0 --port 8000"]

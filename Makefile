.PHONY: install ingest run test lint eval up
install: ; uv sync
ingest:  ; uv run python -m app.ingest
run:     ; uv run uvicorn app.api.main:app --reload --port 8000
test:    ; uv run pytest
lint:    ; uv run ruff check . && uv run ruff format --check .
eval:    ; uv run python -m eval.run --cards
up:      ; docker compose up --build

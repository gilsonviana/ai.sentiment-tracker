.PHONY: setup install run ui test lint freeze clean-db check-python \
        client-install client schema \
        docker-up docker-up-dev docker-down docker-logs

SERVER      := server
CLIENT      := client
VENV        := $(SERVER)/.venv
PYTHON      := $(VENV)/bin/python
PIP         := $(VENV)/bin/pip
UVICORN     := $(VENV)/bin/uvicorn
STREAMLIT   := $(VENV)/bin/streamlit
PYTEST      := $(VENV)/bin/pytest
REQUIRED_PY := 3.12

# ── Python version guard ──────────────────────────────────────────────────────
check-python:
	@ACTUAL=$$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2); \
	if [ "$$ACTUAL" != "$(REQUIRED_PY)" ]; then \
		echo ""; \
		echo "Wrong Python version: $$ACTUAL (need $(REQUIRED_PY))"; \
		echo "Install it from https://www.python.org/downloads/"; \
		echo ""; \
		exit 1; \
	fi

# ── Environment setup ─────────────────────────────────────────────────────────
venv: check-python
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

setup: venv
	cp -n .env.example .env || true
	mkdir -p data
	@echo ""
	@echo "Setup complete. Run 'make install' next."

# ── Dependency install ────────────────────────────────────────────────────────
install: venv
	@if [ -f $(SERVER)/requirements.lock ]; then \
		echo "Installing from lockfile..."; \
		$(PIP) install -r $(SERVER)/requirements.lock; \
	else \
		echo "No lockfile found. Installing from requirements.txt..."; \
		$(PIP) install -r $(SERVER)/requirements.txt; \
	fi

# ── Freeze lockfile ───────────────────────────────────────────────────────────
freeze:
	$(PIP) freeze > $(SERVER)/requirements.lock
	@echo "requirements.lock updated."

# ── Dev — server ─────────────────────────────────────────────────────────────
# PYTHONPATH=server lets Python resolve `from app.xxx` while the cwd stays at
# repo root, keeping .env and data/ paths consistent (no cd required).
run:
	PYTHONPATH=$(SERVER) $(UVICORN) app.main:app --reload --port 8000

ui:
	PYTHONPATH=$(SERVER) $(STREAMLIT) run $(SERVER)/ui/app.py --server.port 8501

test:
	PYTHONPATH=$(SERVER) $(PYTEST) $(SERVER)/tests/ -v

lint:
	$(VENV)/bin/ruff check $(SERVER)/app/ $(SERVER)/tests/

clean-db:
	rm -f data/journal.db
	rm -rf data/chroma
	@echo "Database cleared. Run 'make run' to recreate."

# ── Dev — client ──────────────────────────────────────────────────────────────
client-install:
	cd $(CLIENT) && npm ci

client:
	cd $(CLIENT) && npm run dev

# ── OpenAPI schema + TypeScript type generation ───────────────────────────────
# Requires the API to be running locally (make run in another terminal).
schema:
	@echo "Fetching OpenAPI schema from running API..."
	curl -sf http://localhost:8000/openapi.json -o openapi.json
	@echo "Generating TypeScript types..."
	cd $(CLIENT) && npx openapi-typescript ../openapi.json -o src/types/api.gen.ts
	@echo "Done. Commit openapi.json and client/src/types/api.gen.ts."

# ── Docker ────────────────────────────────────────────────────────────────────
docker-up:
	docker compose up --build -d

docker-up-dev:
	docker compose --profile dev up --build -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

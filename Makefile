.PHONY: install setup run ui test lint check-python freeze clean-db reset reset-confirm seed seed-process

VENV        := .venv
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
		echo "❌  Wrong Python version: $$ACTUAL"; \
		echo "   This project requires Python $(REQUIRED_PY).x"; \
		echo "   Install it from https://www.python.org/downloads/"; \
		echo "   Then re-run: make setup"; \
		echo ""; \
		exit 1; \
	else \
		echo "✅  Python $$ACTUAL — OK"; \
	fi

# ── Environment setup ─────────────────────────────────────────────────────────
venv: check-python
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

setup: venv
	cp -n .env.example .env || true
	mkdir -p data
	@echo ""
	@echo "✅  Setup complete. Run 'make install' next."

# ── Dependency install ────────────────────────────────────────────────────────
install: venv
	@if [ -f requirements.lock ]; then \
		echo "📦  Installing from lockfile (requirements.lock)..."; \
		$(PIP) install -r requirements.lock; \
	else \
		echo "📦  No lockfile found. Installing from requirements.txt..."; \
		$(PIP) install -r requirements.txt; \
		echo ""; \
		echo "💡  Run 'make freeze' to generate a lockfile for reproducible installs."; \
	fi

# ── Freeze lockfile ───────────────────────────────────────────────────────────
freeze:
	$(PIP) freeze > requirements.lock
	@echo "✅  requirements.lock generated. Commit this file to git."

# ── Dev commands ──────────────────────────────────────────────────────────────
run:
	$(UVICORN) app.main:app --reload --port 8000

ui:
	$(STREAMLIT) run ui/app.py --server.port 8501

test:
	$(PYTEST) tests/ -v

lint:
	$(VENV)/bin/ruff check app/ tests/

clean-db:
	rm -f data/journal.db
	rm -rf data/chroma
	@echo "✅  Database cleared. Run 'make run' to recreate."

# ── Reset commands ────────────────────────────────────────────────────────────
reset:
	@echo "⚠️  This will delete ALL user data (journals, embeddings, etc)."
	@echo "   Run 'make reset-confirm' if you really want to proceed."

reset-confirm:
	$(PYTHON) scripts/reset.py

# ── Seed commands ─────────────────────────────────────────────────────────────
seed:
	$(PYTHON) scripts/seed.py
	@echo ""
	@echo "💡  Tip: Use 'make seed-process' to also enqueue entries for analysis."

seed-process:
	$(PYTHON) scripts/seed.py --process
	@echo ""
	@echo "✅  Entries seeded and enqueued for processing."

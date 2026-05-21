.PHONY: install setup run test lint venv

VENV     := .venv
PYTHON   := $(VENV)/bin/python
PIP      := $(VENV)/bin/pip
UVICORN  := $(VENV)/bin/uvicorn
PYTEST   := $(VENV)/bin/pytest

venv:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

setup: venv
	cp -n .env.example .env || true
	mkdir -p data

install: venv
	$(PIP) install -r requirements.txt

run:
	$(UVICORN) app.main:app --reload --port 8000

test:
	$(PYTEST) tests/ -v

lint:
	$(VENV)/bin/ruff check app/ tests/
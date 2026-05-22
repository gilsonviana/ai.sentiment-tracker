# CLAUDE.md — AI Sentiment Tracker

## Project Overview

A FastAPI-based journaling API that runs an async ML pipeline on every entry: VADER + RoBERTa sentiment scoring and SentenceTransformer embeddings. Results are stored in SQLite (metadata) and Chroma (vectors). Entries are processed asynchronously through a SQLite-backed queue worker. Ollama/Mistral is used for weekly reflection summaries. All ML models run locally.

## Tech Stack

- **Python 3.12** (exact version required — binary wheel compatibility)
- **FastAPI + Uvicorn** — async web framework, OpenAPI auto-docs at `/docs`
- **Pydantic v2 + pydantic-settings** — schema validation and `.env` config
- **aiosqlite** — async SQLite driver; `aiosqlite` + raw SQL (no ORM)
- **Chroma 1.5.9** — local persistent vector store
- **HuggingFace Transformers** — RoBERTa sentiment (`cardiffnlp/twitter-roberta-base-sentiment-latest`)
- **SentenceTransformers** — `all-MiniLM-L6-v2` (384-dim embeddings)
- **vaderSentiment** — rule-based baseline scorer
- **Ollama** — external LLM backend (`mistral:7b`) for reflections
- **pytest + pytest-asyncio** — tests run in `asyncio_mode = "auto"`
- **Ruff** — linting (`line-length = 88`, target `py312`)
- **Streamlit** — lightweight dev UI at `http://localhost:8501`

## Commands

```bash
# First-time setup (creates .venv, .env, data/)
make setup

# Install dependencies (uses requirements.lock)
make install

# Run the API (http://localhost:8000)
make run

# Run the Streamlit UI (http://localhost:8501) — requires API running
make ui

# Tests
make test

# Lint
make lint

# Regenerate lockfile after changing requirements.txt
make freeze
```

Ollama must be running before starting the API:
```bash
ollama serve   # Terminal 1
make run       # Terminal 2
```

Docker alternative:
```bash
docker-compose up --build
```

## Project Structure

```
app/
  main.py           # FastAPI app, lifespan (runs migrations + starts queue worker)
  config.py         # Pydantic settings, reads from .env
  api/
    routes.py       # POST /entries, GET /entries, GET /entries/{id},
                    # GET /entries/{id}/analysis, GET /health, POST /reflect
    deps.py         # DB connection dependency injection
  core/
    pipeline.py     # run_analysis_pipeline — async ML fan-out (opens own DB connection)
    preprocessing.py# Text cleaning and sentence chunking
    worker.py       # Async queue worker loop (poll → claim → process → complete/retry)
  db/
    migrations.py   # Creates entries, analysis, reflections, queue tables
    queue.py        # Queue CRUD: enqueue, claim_next_job, complete_job, fail_job, reset_stale_jobs
    sqlite.py       # Async CRUD operations for entries/analysis/reflections
  models/
    entry.py        # JournalEntryCreate, JournalEntryDB, JournalEntryResponse
    analysis.py     # SentimentResult, AnalysisResult, AnalysisResponse
    reflection.py   # ReflectionResponse
  services/
    sentiment.py    # VADER + RoBERTa composite scoring
    embeddings.py   # SentenceTransformer singleton
    vector_store.py # Chroma client (upsert + similarity search)
    reflection.py   # Weekly reflection: SQLite context fetch, prompt assembly, Ollama call
tests/
  conftest.py       # AsyncClient fixture via ASGITransport
  unit/
    test_preprocessing.py
ui/
  app.py            # Streamlit frontend — write entries, browse history, health check
data/               # Runtime only — gitignored
  journal.db
  chroma/
```

## Architecture

### Request Lifecycle

1. `POST /entries` → saves entry to SQLite with `status=pending`, enqueues a job in the `queue` table, returns `202 Accepted`
2. Queue worker (asyncio task, started in lifespan) polls every 2 seconds, claims the next job
3. Pipeline runs sentiment scoring and embeddings concurrently via `asyncio.gather`; CPU-bound calls go to thread pool via `executor`
4. Results written to SQLite `analysis` table and Chroma vector store
5. Entry `status` updated: `pending` → `processed` (or `failed`); job row deleted on success
6. Client polls `GET /entries/{id}` to check status
7. Once `processed`, client fetches `GET /entries/{id}/analysis` for scores

### Queue Worker

The queue is backed by the existing SQLite database — no additional infrastructure required. Key properties:

- **Durability** — job survives process restarts; stale `processing` rows are reset to `pending` on startup
- **Retry with backoff** — up to 3 attempts with exponential backoff (5s → 10s → 20s)
- **Dead-letter** — jobs exceeding `max_attempts` are set to `status=failed` with the error stored in the `queue` table

### ML Services

All services are singletons loaded at import time (avoid re-initialization per request). Models are downloaded from HuggingFace Hub on first run — requires `HF_TOKEN` in `.env` to avoid rate limits.

Entity extraction was removed in favour of Mistral-driven analysis in the weekly reflection step, which provides richer structured signals.

### Database Schema

- `entries(id, content, created_at, entry_date, status)` — raw input
- `analysis(entry_id, vader_score, roberta_score, composite_score, label, entities, analysed_at)` — ML output; `entities` is always `[]`
- `queue(id, entry_id, attempts, max_attempts, status, error, enqueued_at, next_attempt_at)` — durable job queue

## Environment Variables

Copy `.env.example` to `.env`:

```
APP_NAME="AI Journal"
DEBUG=false
DB_PATH=./data/journal.db
CHROMA_PATH=./data/chroma
EMBEDDING_MODEL=all-MiniLM-L6-v2
ROBERTA_MODEL=cardiffnlp/twitter-roberta-base-sentiment-latest
OLLAMA_URL=http://localhost:11434
HF_TOKEN=<your-huggingface-token>
```

## Runtime Requirements

- ~8 GB RAM (Mistral 7B model)
- ~4.1 GB disk for model weights (Mistral ~4.1 GB, RoBERTa/MiniLM ~400 MB)
- Ollama installed and `mistral` model pulled (`ollama pull mistral`)
- HuggingFace token for model downloads

## Testing

Tests use `asyncio_mode = "auto"` — no need for `@pytest.mark.asyncio` decorator. The async `client` fixture in `conftest.py` uses `httpx.AsyncClient` + `ASGITransport` for integration tests.

Integration tests directory exists but is empty — unit tests cover preprocessing logic only.


## V3 Roadmap
- **React frontend** — production UI replacing Streamlit.

### Internationalisation
- **PT-BR support** — swap models: `pysentimiento` for sentiment, `paraphrase-multilingual-MiniLM-L12-v2` for embeddings.

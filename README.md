# AI Journal

Sentiment-aware personal journal with a fully local, zero-cost ML pipeline.

Write journal entries via the API or UI. Every entry is asynchronously scored by VADER + RoBERTa sentiment models, embedded with SentenceTransformers, and named-entity-tagged by BERT-NER. Results are stored in SQLite and a local Chroma vector store. Ollama/Mistral generates weekly reflections and answers freeform questions about your entries using RAG.

---

## Repository layout

```
ai.sentiment-tracker/
├── server/                 # FastAPI backend (Python 3.12)
│   ├── app/                # Application package
│   │   ├── api/            # Route definitions
│   │   ├── core/           # ML pipeline orchestration
│   │   ├── db/             # SQLite migrations + CRUD
│   │   ├── models/         # Pydantic request/response schemas
│   │   └── services/       # Sentiment, embeddings, NER, Chroma, Ollama
│   ├── ui/                 # Streamlit dev UI
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.lock
├── client/                 # React + TypeScript frontend (V3)
│   ├── src/
│   │   ├── api/            # Typed fetch wrappers (entries, reflect, chat, mood)
│   │   └── types/          # api.gen.ts — auto-generated from OpenAPI schema
│   ├── vite.config.ts
│   └── Dockerfile
├── scripts/
│   └── ollama-entrypoint.sh  # Pulls mistral on first Docker run
├── data/                   # Runtime only — gitignored (SQLite + Chroma)
├── openapi.json            # Committed OpenAPI schema snapshot
├── docker-compose.yml
└── Makefile
```

---

## Requirements

| Requirement | Version | Notes |
|---|---|---|
| Python | **3.12.x exactly** | Binary wheel compatibility |
| Node.js | 18 + | For the React client |
| Ollama | latest | Local LLM runtime — not needed for Docker path |
| Docker + Compose | V2 | Optional — spins up everything in one command |

> **Why Python 3.12 only?** Several ML packages (`pydantic-core`, `torch`, `onnxruntime`)
> ship pre-built wheels for 3.12. Python 3.13 broke binary ABI compatibility for many of
> these libraries. Until the ecosystem catches up, 3.12 is the stable target.

---

## Quick start — local development

### 1. Python 3.12

```bash
python3 --version   # must show 3.12.x
```

If you have a different version, use `pyenv`:

```bash
brew install pyenv
pyenv install 3.12
# .python-version in server/ tells pyenv to activate it automatically
```

### 2. Ollama

```bash
# macOS
brew install ollama

# Pull the model weights (~4.1 GB, one-time)
ollama pull mistral
```

> **RAM requirement:** Mistral 7B needs ~8 GB of available RAM.
> On Apple Silicon it runs on the Neural Engine (~30–40 tok/s).
> On CPU it is functional but slower.

### 3. Project setup

```bash
git clone <repo-url>
cd ai.sentiment-tracker

# Create server/.venv, copy .env.example → .env, create data/
make setup

# Install Python dependencies from lockfile
make install
```

### 4. Configure `.env`

The generated `.env` is pre-filled with safe defaults. The only value you need to set is
an optional HuggingFace token (removes rate limits on model downloads):

```bash
# Free at huggingface.co/settings/tokens
echo 'HF_TOKEN=hf_your_token_here' >> .env
```

### 5. Run

```bash
# Terminal 1 — Ollama (skip if already running as a system service)
ollama serve

# Terminal 2 — FastAPI (http://localhost:8000/docs)
make run

# Terminal 3 — Streamlit dev UI (http://localhost:8501)
make ui

# Terminal 4 — React dev server (http://localhost:3000)
make client-install
make client
```

---

## Docker — all services in one command

Docker handles Ollama startup and model download automatically. No local Ollama
installation required.

```bash
# Copy env template
cp .env.example .env

# Start API + Ollama (production-like)
make docker-up

# Start API + Ollama + Streamlit UI + React dev server
make docker-up-dev

# View logs
make docker-logs

# Stop everything
make docker-down
```

On first run, the `ollama` container pulls Mistral (~4.1 GB) into a named Docker volume.
Subsequent starts skip the download automatically.

> `docker compose up` starts `api` and `ollama` only.
> `docker compose --profile dev up` also starts `client` (port 3000) and `ui` (port 8501).

---

## Makefile reference

| Command | What it does |
|---|---|
| `make setup` | Create `server/.venv`, copy `.env.example`, create `data/` |
| `make install` | Install Python deps from `server/requirements.lock` |
| `make run` | Start FastAPI on port 8000 (hot-reload) |
| `make ui` | Start Streamlit dev UI on port 8501 |
| `make test` | Run pytest |
| `make lint` | Ruff linter |
| `make freeze` | Regenerate `server/requirements.lock` |
| `make clean-db` | Delete `data/journal.db` and `data/chroma/` |
| `make client-install` | `npm ci` inside `client/` |
| `make client` | Start React dev server on port 3000 |
| `make schema` | Export `openapi.json` + regenerate `client/src/types/api.gen.ts` |
| `make docker-up` | Build and start `api` + `ollama` |
| `make docker-up-dev` | Build and start all services including `client` + `ui` |
| `make docker-down` | Stop all containers |
| `make docker-logs` | Tail all container logs |

---

## API

Interactive docs at `http://localhost:8000/docs`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/entries` | Submit a journal entry (202, async pipeline) |
| `GET` | `/entries` | List entries (`?month=YYYY-MM` to filter) |
| `GET` | `/entries/{id}` | Poll processing status |
| `GET` | `/entries/{id}/analysis` | Fetch sentiment scores + named entities |
| `GET` | `/reflect` | List stored reflections |
| `POST` | `/reflect` | Generate a reflection (`?start=YYYY-MM-DD&end=YYYY-MM-DD`) |
| `POST` | `/chat` | Ask a question about your journal (RAG + Ollama) |
| `GET` | `/mood/{month}` | Monthly mood report — dates + scores for charting |

### Entry lifecycle

1. `POST /entries` → `202 Accepted` with `entry_id`, status `pending`
2. Background task runs VADER + RoBERTa + NER + embeddings concurrently
3. Results written to SQLite and Chroma; status updates to `processed` (or `failed`)
4. Poll `GET /entries/{id}` until status is `processed`
5. Fetch `GET /entries/{id}/analysis` for scores and entities

---

## TypeScript API contract

TypeScript interfaces are auto-generated from the committed `openapi.json`:

```bash
# Requires the API to be running
make schema
# → writes openapi.json (root) and client/src/types/api.gen.ts
```

Commit both files whenever routes or models change. The `client/src/api/` layer imports
types directly from the generated file — no manual interface maintenance needed.

---

## Streamlit dev UI

A full-featured testing harness covering every API endpoint, available at
`http://localhost:8501` via `make ui`.

| Tab | Functionality |
|---|---|
| Write Entry | Submit entries with a date picker; polls for analysis and displays scores + entity chips |
| Browse Entries | Filter by month, status, or keyword; expandable analysis per entry |
| Reflection | Generate reflections with optional date range; view past reflections |
| Chat | Ask freeform questions about your journal entries (RAG) |
| Insights | Monthly mood line chart from `/mood/{month}` |
| API Health | Liveness check + endpoint reference |

---

## Stack

| Layer | Tool |
|---|---|
| API | FastAPI + Uvicorn |
| Validation | Pydantic v2 + pydantic-settings |
| Storage | SQLite via aiosqlite (no ORM) |
| Vector store | Chroma (local persistent, cosine similarity) |
| Sentiment | VADER + RoBERTa (`cardiffnlp/twitter-roberta-base-sentiment-latest`) |
| Embeddings | `all-MiniLM-L6-v2` (384-dim, SentenceTransformers) |
| NER | `dslim/bert-base-NER` (confidence threshold > 0.85) |
| LLM | Ollama — `mistral` (reflections + RAG chat) |
| Dev UI | Streamlit |
| Client | React 19 + TypeScript + Vite |
| API types | openapi-typescript (generated from FastAPI schema) |

---

## Testing

```bash
make test
```

Tests use `pytest-asyncio` in `auto` mode. The `conftest.py` fixture spins up the FastAPI
app via `httpx.AsyncClient + ASGITransport` — no running server needed.

---

## Runtime requirements

- ~8 GB RAM (Mistral 7B)
- ~4.5 GB disk for model weights (Mistral ~4.1 GB, BERT models ~400 MB)
- Ollama installed with `mistral` pulled — or use Docker (pulls automatically)

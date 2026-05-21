# AI Journal

Sentiment-aware personal journal with a fully local, zero-cost ML pipeline.

## Requirements

| Requirement | Version |
|---|---|
| Python | **3.12.x exactly** (not 3.11, not 3.13) |
| pip | 24+ |
| OS | macOS, Linux, Windows (WSL2) |

> **Why 3.12 only?** Several ML packages (`pydantic-core`, `thinc`) ship
> pre-built wheels for 3.12. Python 3.13 broke binary ABI compatibility for
> many of these libraries. Until the ecosystem catches up, 3.12 is the
> stable target.

### Check your Python version

```bash
python3 --version   # must show 3.12.x
```

If you have the wrong version, download 3.12 from
https://www.python.org/downloads/ and re-run setup.

## Quickstart

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd ai.sentiment-tracker

# 2. Setup environment (checks Python version, creates .venv, copies .env)
make setup

# 3. Install dependencies
#    - Uses requirements.lock if present (fast, reproducible)
#    - Falls back to requirements.txt if not (resolves from scratch)
make install

# 4. Add your HuggingFace token to .env (free at huggingface.co/settings/tokens) (optional)
echo 'HF_TOKEN=hf_your_token_here' >> .env

# 5. Run the server
make run
# → http://localhost:8000/docs
```

## Generating a lockfile (first time or after changing deps)

```bash
make freeze
git add requirements.lock
git commit -m "chore: update lockfile"
```

The lockfile (`requirements.lock`) pins every transitive dependency to exact
versions that are known to work together. Anyone cloning the repo will
install the identical environment via `make install`.

## Stack

| Layer | Tool |
|---|---|
| API | FastAPI + uvicorn |
| Validation | Pydantic v2 |
| Raw storage | SQLite (aiosqlite) |
| Sentiment | VADER + RoBERTa (cardiffnlp) |
| Embeddings | all-MiniLM-L6-v2 |
| NER | dslim/bert-base-NER |
| Vector store | Chroma (local persistent) |
| LLM reflection | Ollama (mistral:7b) |
| Frontend | Streamlit |

## API

- `POST /entries` — submit a journal entry (202, async processing)
- `GET /entries/{id}` — poll processing status
- `GET /health` — liveness check
- `GET /docs` — interactive OpenAPI UI

## Testing

```bash
make test
```

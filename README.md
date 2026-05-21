# AI Journal

Sentiment-aware personal journal with a fully local, zero-cost ML pipeline.

## Stack
| Layer | Tool |
|---|---|
| API | FastAPI + uvicorn |
| Validation | Pydantic v2 |
| Raw storage | SQLite (aiosqlite) |
| Sentiment | VADER + RoBERTa (cardiffnlp) |
| Embeddings | all-MiniLM-L6-v2 |
| NER | spaCy en_core_web_sm |
| Vector store | Chroma (local persistent) |
| LLM reflection | Ollama (mistral:7b) |
| Frontend | Streamlit |

## Quickstart
```bash
make setup      # copy .env, create data/
make install    # pip install + spacy model
make run        # uvicorn on :8000
```

## API
- `POST /entries` — submit a journal entry (202 Accepted, async processing)
- `GET /entries/{id}` — poll processing status
- `GET /health` — liveness check
- `GET /docs` — auto-generated OpenAPI UI

## Testing
```bash
make test
```
